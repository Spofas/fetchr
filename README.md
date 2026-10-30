# fetchr

Fetchr provides a cached USD cryptocurrency market snapshot from CoinGecko as JSON and CSV.

Run with Python 3.10+: `COINGECKO_API_KEY=your-demo-key python3 app.py` (keep the key private). The server listens on port 8000 and refreshes on startup and hourly. It retains its last complete snapshot in `data/snapshot.json`; requests return 503 until a snapshot is available.

Administrator settings: `FETCHR_ASSET_COUNT` (default 3000), `FETCHR_REFRESH_SECONDS` (default 3600), `FETCHR_PORT` (default 8000), and `FETCHR_DATA_DIR` (default `data`). Verify your CoinGecko plan's quota and redistribution terms. At 250 assets per request, a refresh takes at least `ceil(count / 250)` upstream requests; leave room for retries and overlapping pages. A live 3,000-asset refresh succeeded, but monthly quota has not been verified.

`GET /v1/assets?limit=100&offset=0` returns a page, `GET /v1/assets/{coingecko_id}` returns one asset, and `GET /v1/assets.csv` downloads the snapshot. Google Sheets can import a publicly hosted CSV with `=IMPORTDATA("https://your-host/v1/assets.csv")`; Excel can use Data → From Web. Spreadsheet refresh timing is independent of the server schedule.

The fields include CoinGecko ID, rank, name, symbol, USD price, market cap, FDV, rolling 24-hour percentage price change, and source update time. Missing values are null in JSON and blank in CSV. The JSON listing includes the time fetchr completed the snapshot. Rankings may change while pages are being fetched, so the snapshot is an approximation rather than an atomic ranking; repeated IDs are deduplicated. Data is supplied by CoinGecko. Category filters and historical data are not implemented.

Run tests with `python3 -m unittest discover -s tests -v`.
