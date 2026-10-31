# fetchr

Fetchr publishes a static USD cryptocurrency market snapshot from CoinGecko as a web page, JSON, and CSV. The default target is 3,000 assets, refreshed by GitHub Actions approximately hourly. No application server or server-side queries are required for the static site.

## GitHub Pages setup

1. Merge the workflow into the repository's default branch (`main`). GitHub scheduled workflows run from the default branch.
2. In repository Settings → Secrets and variables → Actions, add the CoinGecko Demo API key as the `COINGECKO_API_KEY` repository secret. Do not put the key in the repository or chat. The cloud environment's key does not automatically transfer to GitHub.
3. In Settings → Pages, set the build and deployment source to **GitHub Actions**.
4. Run **Refresh and deploy market data** from Actions, or wait for the next scheduled run. The workflow publishes the complete `site` folder to GitHub Pages. If generation fails, it does not deploy, so the previous successful Pages deployment remains available.

Set repository Actions variable `FETCHR_ASSET_COUNT` to change the default asset count. To change the refresh schedule, edit the cron expression in `.github/workflows/pages.yml`. Scheduled GitHub Actions can be delayed. Confirm GitHub Actions and CoinGecko limits and redistribution terms for your account before relying on this schedule. Each refresh needs at least `ceil(count / 250)` requests, plus any overlap pages or retries. The free-tier monthly quota has not been verified. The homepage excludes stablecoins and liquid-staking tokens using CoinGecko categories, which may be incomplete. Category data is fetched once per UTC day using a GitHub Actions cache and adds additional API calls. The CSV and JSON include the full snapshot.

## Local generation

With Python 3.10 or newer, configure `COINGECKO_API_KEY` securely in your environment and run `python3 categories.py` followed by `python3 generate.py`. It writes `site/assets.json`, `site/assets.csv`, and `site/categories.json`; source data is retained under the ignored `data/` directory. `FETCHR_ASSET_COUNT`, `FETCHR_DATA_DIR`, and `FETCHR_OUTPUT_DIR` can be set as environment variables. The category file must be in the configured data directory. Remove or refresh `data/categories.json` to update the categories locally. Serve `site/` with a static web server to inspect the page; generated files are ignored by Git.

In Google Sheets use `=IMPORTDATA("https://your-pages-url/assets.csv")`. In Excel choose Data → From Web and use that URL. Spreadsheet refresh timing is independent of fetchr. The JSON includes source, currency, snapshot completion time and an assets array.

Fields include CoinGecko ID, market-cap rank, name, ticker, USD price, market cap, fully diluted valuation, rolling 24-hour percentage price change, source update time, image URL, 24-hour trading volume, all-time-high price and date, and percentage change from all-time high. The new fields are appended to preserve existing CSV column positions. Missing values are null in JSON and blank in CSV. Rankings may move while upstream pages are fetched, so the snapshot approximates the top assets; repeated IDs are deduplicated. Data is provided by CoinGecko. Category exclusions and historical data are not implemented for the downloads.

Run tests with `python3 -m unittest discover -s tests -v`. The earlier `app.py` HTTP server remains available for local compatibility but is not deployed by the static workflow.
