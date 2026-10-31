# fetchr

Fetchr publishes a USD cryptocurrency market snapshot sourced from CoinGecko. The default target is **2,500 assets**, updated by GitHub Actions at minute 09 of each hour in UTC. GitHub may delay scheduled jobs. The last successful deployment stays available if a refresh fails. The site is static: it has no continuously running server or server-side query API.

- [Open fetchr](https://spofas.github.io/fetchr/)
- [Download the full CSV](https://spofas.github.io/fetchr/assets.csv)
- [View or download the full JSON](https://spofas.github.io/fetchr/assets.json)
- [View refresh runs](https://github.com/Spofas/fetchr/actions/workflows/pages.yml)

## Using the data

The homepage previews the first 15 assets by market cap after excluding IDs in CoinGecko's stablecoin and liquid-staking-token categories. The preview includes icons where available. These classifications may be incomplete; they apply to the preview only. The full CSV and JSON include all assets in the snapshot.

The field selector on the page produces custom CSV and JSON downloads and a Google Sheets formula for the selected columns. Custom downloads are snapshots created in the browser; they do not update automatically. The formula imports the full CSV and selects the chosen columns when Google Sheets refreshes it. Copy buttons are available for the formulas and full-file URLs.

The homepage shows snapshot freshness using color and text: green **Fresh** for up to 90 minutes, amber **Update overdue** for 90 minutes to 3 hours, and red **Stale data** beyond 3 hours. It displays the age and UTC timestamp and recalculates the age every minute using the visitor's device clock. This describes the loaded snapshot, not the status of the scheduler or the update time of every individual asset. Reload the page to retrieve the latest published snapshot.

To import the complete dataset into Google Sheets, enter:

```text
=IMPORTDATA("https://spofas.github.io/fetchr/assets.csv")
```

For Excel, download the CSV or use **Data → From Web** with the CSV URL. Spreadsheet applications control their own refresh timing independently of fetchr.

## Snapshot fields

CSV columns are in the following order. Preserve existing column positions when extending the schema: the page's generated Sheets formulas depend on them. USD amounts come from CoinGecko. Missing values are empty in CSV and `null` in JSON.

| Column | Field | Meaning |
| ---: | --- | --- |
| 1 | `id` | CoinGecko asset ID |
| 2 | `market_cap_rank` | Market-cap rank |
| 3 | `name` | Asset name |
| 4 | `symbol` | Ticker |
| 5 | `current_price` | USD price |
| 6 | `market_cap` | USD market capitalization |
| 7 | `fully_diluted_valuation` | USD fully diluted valuation |
| 8 | `price_change_percentage_24h` | Rolling 24-hour price change (%) |
| 9 | `last_updated` | Provider's asset update time |
| 10 | `image` | CoinGecko icon URL |
| 11 | `total_volume` | 24-hour trading volume in USD |
| 12 | `ath` | All-time-high price in USD |
| 13 | `ath_date` | Date and time of the all-time high |
| 14 | `ath_change_percentage` | Percentage change from all-time high, usually negative below the high |

The full JSON contains `source`, `currency`, `snapshot_at` (when fetchr completed its fetch), and `assets`. Custom JSON also records the selected `fields`. CoinGecko updates individual assets at different times. Rankings can move between upstream pages, so the fetched order is an approximation; repeated IDs are deduplicated. No historical time series is maintained.

## Configuration and deployment

The workflow in [`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs on pushes to `main`, manual dispatch, and `9 * * * *` (minute 09 of each hour UTC). Scheduled GitHub Actions are not guaranteed to start exactly on time. The repository variable `FETCHR_ASSET_COUNT` overrides the default of `2500`; configure it under **Settings → Secrets and variables → Actions → Variables**. Changing the variable takes effect on the next run. Edit the cron expression on the default branch to change the schedule.

To set up a deployment:

1. Put the workflow on the default branch (`main`); scheduled workflows run there.
2. Add a CoinGecko Demo key as the repository Actions secret `COINGECKO_API_KEY`. Never commit the key or share it in chat. Cloud environment secrets do not automatically transfer to GitHub.
3. Under **Settings → Pages**, select **GitHub Actions** as the source.
4. Run **Refresh and deploy market data** from the Actions tab, or wait for a scheduled run. The workflow generates a complete snapshot before deploying. A failed run leaves the last successful Pages deployment in place.

At 250 assets per request, a 2,500-asset refresh needs at least 10 market requests. Additional calls may be needed for overlapping pages, retries, manual runs, and category data. Category IDs are cached by UTC day in GitHub Actions; cache misses can cause extra category requests. GitHub Actions and CoinGecko limits and redistribution terms should be checked for the account in use. The CoinGecko free-tier monthly quota has not been verified.

## Local development

Python 3.10 or newer is required; there are no third-party Python dependencies. Set `COINGECKO_API_KEY` securely in the environment, then run:

```sh
python3 categories.py
python3 generate.py
python3 -m http.server 8000 --directory site
```

The first command writes `data/categories.json` if absent; remove that file when a fresh category fetch is needed. The generator writes `site/assets.json`, `site/assets.csv`, and `site/categories.json`; generated files and source data are ignored by Git. `FETCHR_ASSET_COUNT` and `FETCHR_OUTPUT_DIR` override the count and output directory. `FETCHR_DATA_DIR` overrides the generator's data directory, but `categories.py` always writes to `data/`: if using a different directory, place `categories.json` there before generating. Never commit generated files containing secrets.

Run the tests with `python3 -m unittest discover -s tests -v`. The earlier `app.py` HTTP server remains for local compatibility; GitHub Pages does not run it.

Data supplied by [CoinGecko](https://www.coingecko.com/); it is not investment advice.
