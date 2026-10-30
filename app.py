"""Cached CoinGecko market data service; requires only the Python standard library."""
import csv
import html
import io
import json
import logging
import math
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

FIELDS = ("id", "market_cap_rank", "name", "symbol", "current_price", "market_cap",
          "fully_diluted_valuation", "price_change_percentage_24h", "last_updated")
MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
log = logging.getLogger("fetchr")


def positive_int(name, default):
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


class Store:
    def __init__(self, count, directory, api_key="", markets_url=MARKETS_URL):
        self.count, self.directory, self.api_key, self.markets_url = count, Path(directory), api_key, markets_url
        self.path = self.directory / "snapshot.json"
        self.lock = threading.Lock()
        self.snapshot = None
        try:
            with self.path.open(encoding="utf-8") as file:
                saved = json.load(file)
            if isinstance(saved.get("assets"), list) and saved.get("snapshot_at"):
                self.snapshot = saved
        except (OSError, ValueError, AttributeError):
            pass

    def refresh(self):
        assets, seen = [], set()
        # Rankings can move between upstream pages. Allow a few extra pages to
        # compensate for overlap, but fail safely if completeness is elusive.
        for page in range(1, math.ceil(self.count / 250) + 4):
            params = urlencode({"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250,
                                "page": page, "sparkline": "false"})
            headers = {"Accept": "application/json", "User-Agent": "fetchr/1.0"}
            if self.api_key:
                headers["x-cg-demo-api-key"] = self.api_key
            with urlopen(Request(self.markets_url + "?" + params, headers=headers), timeout=30) as response:
                data = json.load(response)
            if not isinstance(data, list) or not data:
                raise ValueError(f"Incomplete page {page}")
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                    raise ValueError(f"Invalid asset on page {page}")
                if item["id"] in seen:
                    continue
                seen.add(item["id"])
                assets.append({key: item.get(key) for key in FIELDS})
                if len(assets) == self.count:
                    break
            if len(assets) == self.count:
                break
        if len(assets) != self.count:
            raise ValueError(f"Incomplete snapshot: received {len(assets)} unique assets; expected {self.count}")
        snapshot = {"source": "CoinGecko", "currency": "usd",
                    "snapshot_at": datetime.now(timezone.utc).isoformat(), "assets": assets}
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory, delete=False) as file:
                temporary = file.name
                json.dump(snapshot, file, allow_nan=False)
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        with self.lock:
            self.snapshot = snapshot
        log.info("Published %d assets", len(assets))

    def get(self):
        with self.lock:
            return self.snapshot


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def json_response(self, status, value):
            self.send_bytes(status, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            url = urlsplit(self.path)
            snapshot = store.get()
            if url.path == "/":
                status = (f"{len(snapshot['assets'])} assets; snapshot: {snapshot['snapshot_at']}"
                          if snapshot else "No complete snapshot available yet.")
                page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>fetchr</title>
<h1>fetchr</h1><p>USD cryptocurrency market data from CoinGecko.</p><p>{html.escape(status)}</p>
<h2>Use the data</h2><p><a href="/v1/assets">JSON API</a> · <a href="/v1/assets.csv">Download CSV</a></p>
<p>Use <code>/v1/assets?limit=100&amp;offset=0</code> to page through results, or
<code>/v1/assets/bitcoin</code> for one CoinGecko ID.</p>
<p>Import the CSV URL into Google Sheets with IMPORTDATA or Excel with Data → From Web.</p>
<p>Columns: CoinGecko ID, rank, name, symbol, USD price, market cap, fully diluted valuation,
rolling 24-hour percentage change, and source update time. Missing values are blank in CSV.
Data provided by CoinGecko. Consult your plan's terms before redistribution.</p></html>'''
                return self.send_bytes(200, page.encode(), "text/html; charset=utf-8")
            if not (url.path == "/v1/assets" or url.path == "/v1/assets.csv" or url.path.startswith("/v1/assets/")):
                return self.json_response(404, {"error": "Not found"})
            if snapshot is None:
                return self.json_response(503, {"error": "No complete snapshot available"})
            assets = snapshot["assets"]
            if url.path == "/v1/assets.csv":
                out = io.StringIO(newline="")
                writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
                writer.writeheader()
                for item in assets:
                    writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value)
                                     for key, value in item.items()})
                return self.send_bytes(200, out.getvalue().encode(), "text/csv; charset=utf-8")
            if url.path.startswith("/v1/assets/"):
                asset_id = unquote(url.path[len("/v1/assets/"):])
                asset = next((item for item in assets if item["id"] == asset_id), None)
                return self.json_response(200, asset) if asset else self.json_response(404, {"error": "Asset not found"})
            try:
                params = parse_qs(url.query)
                limit = int(params.get("limit", [str(min(100, store.count))])[0])
                offset = int(params.get("offset", ["0"])[0])
                if limit < 1 or limit > store.count or offset < 0:
                    raise ValueError
            except ValueError:
                return self.json_response(400, {"error": "Invalid limit or offset"})
            result = {key: snapshot[key] for key in ("source", "currency", "snapshot_at")}
            result.update(total=len(assets), count=len(assets[offset:offset + limit]), offset=offset,
                          assets=assets[offset:offset + limit])
            self.json_response(200, result)
    return Handler


def main():
    logging.basicConfig(level=logging.INFO)
    count = positive_int("FETCHR_ASSET_COUNT", 3000)
    interval = positive_int("FETCHR_REFRESH_SECONDS", 3600)
    port = positive_int("FETCHR_PORT", 8000)
    store = Store(count, os.getenv("FETCHR_DATA_DIR", "data"), os.getenv("COINGECKO_API_KEY", ""))

    def worker():
        while True:
            try:
                store.refresh()
            except Exception as exc:
                log.warning("Refresh failed; retaining last snapshot: %s", exc)
            time.sleep(interval)

    threading.Thread(target=worker, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", port), handler_for(store)).serve_forever()


if __name__ == "__main__":
    main()
