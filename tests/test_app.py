import csv
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

from app import Store, handler_for
from generate import generate


class Provider(BaseHTTPRequestHandler):
    fail_page = None
    pages = []
    overlap = False

    def do_GET(self):
        page = int(parse_qs(urlsplit(self.path).query)["page"][0])
        type(self).pages.append(page)
        if page == self.fail_page:
            self.send_error(500)
            return
        items = [{"id": f"coin-{i}", "name": f"Coin {i}", "symbol": f"c{i}",
                  "market_cap_rank": i, "current_price": i, "market_cap": i * 10,
                  "fully_diluted_valuation": None, "price_change_percentage_24h": 1.5,
                  "last_updated": "2026-01-01T00:00:00Z"}
                 for i in range((page - 1) * 250 + 1, page * 250 + 1)]
        if self.overlap and page == 2:
            items[0]["id"] = "coin-250"
        body = json.dumps(items).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        Provider.pages, Provider.fail_page, Provider.overlap = [], None, False
        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        threading.Thread(target=self.provider.serve_forever, daemon=True).start()
        self.store = Store(500, self.temp.name, markets_url=f"http://127.0.0.1:{self.provider.server_port}/markets")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.store))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.provider.shutdown()
        self.provider.server_close()
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return response.read().decode()

    def test_refresh_api_csv_and_failure_retains_snapshot(self):
        with self.assertRaises(HTTPError) as error:
            self.get('/v1/assets')
        self.assertEqual(error.exception.code, 503)
        self.store.refresh()
        self.assertEqual(Provider.pages, [1, 2])
        result = json.loads(self.get('/v1/assets?limit=2&offset=249'))
        self.assertEqual(result['total'], 500)
        self.assertEqual([a['id'] for a in result['assets']], ['coin-250', 'coin-251'])
        self.assertEqual(json.loads(self.get('/v1/assets/coin-1'))['current_price'], 1)
        rows = list(csv.DictReader(io.StringIO(self.get('/v1/assets.csv'))))
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[0]['fully_diluted_valuation'], '')
        self.assertIn('500 assets', self.get('/'))
        old = self.store.get()
        Provider.fail_page = 2
        with self.assertRaises(HTTPError):
            self.store.refresh()
        self.assertEqual(self.store.get(), old)
        restored = Store(500, self.temp.name)
        self.assertEqual(restored.get(), old)

    def test_overlapping_pages_fetch_extra_unique_asset(self):
        Provider.overlap = True
        self.store.refresh()
        assets = self.store.get()['assets']
        self.assertEqual(Provider.pages, [1, 2, 3])
        self.assertEqual(len({asset['id'] for asset in assets}), 500)
        self.assertEqual(assets[-1]['id'], 'coin-501')

    def test_static_files_and_failed_refresh(self):
        output = self.temp.name + '/site'
        Path(self.temp.name, 'categories.json').write_text(json.dumps({'excluded_ids': ['coin-1']}), encoding='utf-8')
        generate(output, self.store)
        with open(output + '/assets.json', encoding='utf-8') as f:
            snapshot = json.load(f)
        with open(output + '/assets.csv', encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(snapshot['assets']), 500)
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[0]['id'], snapshot['assets'][0]['id'])
        with open(output + '/categories.json', encoding='utf-8') as f:
            self.assertEqual(json.load(f)['excluded_ids'], ['coin-1'])
        Provider.fail_page = 2
        with self.assertRaises(HTTPError):
            generate(output, self.store)
        with open(output + '/assets.json', encoding='utf-8') as f:
            self.assertEqual(json.load(f), snapshot)


if __name__ == '__main__':
    unittest.main()
