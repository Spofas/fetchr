// Cloudflare module Worker. GitHub and CoinGecko secrets never go to the webpage.
const API = 'https://api.github.com';

export async function dispatch(env, fetcher = fetch) {
  if (!env.GITHUB_TOKEN) throw new Error('GITHUB_TOKEN secret is missing');
  const headers = {
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'fetchr-cloudflare-scheduler',
  };
  const root = `${API}/repos/Spofas/fetchr/actions/workflows/pages.yml`;
  // Avoid queueing another refresh while a recent one is already running.
  const runs = await fetcher(`${root}/runs?branch=main&per_page=10`, {
    headers, signal: AbortSignal.timeout(15000),
  });
  if (!runs.ok) throw new Error(`GitHub workflow lookup failed: HTTP ${runs.status}`);
  const data = await runs.json();
  if (!Array.isArray(data.workflow_runs)) throw new Error('Invalid GitHub workflow response');
  if (data.workflow_runs.some(run => run.status !== 'completed')) {
    return {dispatched: false, reason: 'refresh-already-active'};
  }
  const response = await fetcher(`${root}/dispatches`, {
    method: 'POST', headers: {...headers, 'Content-Type': 'application/json'},
    body: JSON.stringify({ref: 'main'}), signal: AbortSignal.timeout(15000),
  });
  // An uncertain POST outcome is not retried: it may already have been accepted.
  if (response.status !== 204) throw new Error(`GitHub dispatch failed: HTTP ${response.status}`);
  return {dispatched: true};
}

export default {
  async scheduled(controller, env) {
    try {
      const result = await dispatch(env);
      console.log(JSON.stringify({event: 'fetchr-dispatch', scheduledAt: controller.scheduledTime, ...result}));
    } catch (error) {
      // Only controlled errors go to logs; never print response bodies or tokens.
      console.error('fetchr scheduler failed; inspect GitHub Actions and the Worker secret binding');
      throw new Error('fetchr workflow dispatch failed');
    }
  },
  fetch() {
    return new Response('This Worker only runs scheduled jobs.', {status: 404});
  },
};
