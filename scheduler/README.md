# Cloudflare scheduler

This Worker requests a refresh of `Spofas/fetchr` through GitHub's workflow-dispatch API at minute 09 of every hour UTC. GitHub Actions continues to fetch CoinGecko and deploy Pages. Cloudflare dispatch success means GitHub accepted the request, not that fetching or deployment succeeded. Check both the Worker logs and the resulting GitHub Actions run and published snapshot.

## Dashboard setup

1. In Cloudflare **Workers & Pages**, create a Worker named `fetchr-scheduler`. Choose the option to deploy a simple Worker, then open its code editor and replace the sample code with the contents of `worker.js`. Deploy it as a JavaScript module Worker.
2. In GitHub, open your personal **Settings → Developer settings → Personal access tokens → Fine-grained tokens**. Create a token for resource owner **Spofas**, with repository access to **fetchr only** and repository permission **Actions: Read and write**. Set an expiration and plan to rotate it before it expires. Metadata read access is added automatically. No repository contents-write permission is needed.
3. Add this token in the Cloudflare Worker's **Settings → Variables and Secrets** as a **Secret** named `GITHUB_TOKEN`. Do not add it as a plain-text variable, commit it, paste it into chat, or put it in the site. Keep the CoinGecko key in GitHub Actions secrets; Cloudflare does not need it.
4. Enable Worker observability/logs. Add a **Cron Trigger** with expression `9 * * * *` under the Worker's settings/triggers area. Cloudflare dashboard labels may vary. Cron changes can take up to 15 minutes to propagate.
5. At the next scheduled window, inspect Worker logs. `dispatched: true` indicates GitHub accepted the trigger; `refresh-already-active` means another refresh was already queued or running. Errors indicate the dispatch was not confirmed. A browser visit to the Worker URL returns 404 deliberately and does not trigger a refresh.
6. Confirm GitHub has a successful **workflow_dispatch** run caused by the token owner, and verify `assets.json` has a new `snapshot_at`. Then disable the native GitHub cron: create repository Actions variable **`FETCHR_EXTERNAL_SCHEDULER` = `true`**. This skips refreshes from GitHub's native schedule but preserves manual and push-triggered refreshes. Remove the variable or set it to `false` to restore the native schedule.

The token must be renewed before expiration. A single dispatch attempt is made per tick; uncertain POST outcomes are not retried to avoid spending quota on duplicate refreshes. The active-run check reduces overlap but is not an atomic lock across schedulers. Keep the native schedule only during migration; use the Actions variable above after verification. No external alert delivery or completed-run monitoring is configured by this Worker.

## CLI deployment alternative

From this directory, with the Cloudflare Wrangler CLI authenticated, run `wrangler deploy`, then `wrangler secret put GITHUB_TOKEN`. The latter prompts securely for the GitHub token. `wrangler.jsonc` defines the hourly schedule, disables the public workers.dev route, and enables logs. Manage cron changes in Wrangler if you use this route; redeployment replaces dashboard cron settings with the file's values.

## Tests

Run `node worker.test.js` from this directory. No production token or network connection is needed.
