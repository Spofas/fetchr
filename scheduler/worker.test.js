import assert from 'node:assert/strict';
import test from 'node:test';
import worker, {dispatch} from './worker.js';

test('dispatches main with authentication, after checking active runs', async () => {
  const calls = [];
  const result = await dispatch({GITHUB_TOKEN: 'test-only'}, async (url, options) => {
    calls.push({url, options});
    return calls.length === 1 ? Response.json({workflow_runs: [{status: 'completed'}]}) : new Response(null, {status: 204});
  });
  assert.equal(result.dispatched, true);
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer test-only');
  assert.deepEqual(JSON.parse(calls[1].options.body), {ref: 'main'});
});

test('does not queue duplicate active refreshes', async () => {
  let calls = 0;
  const result = await dispatch({GITHUB_TOKEN: 'test-only'}, async () => {
    calls++;
    return Response.json({workflow_runs: [{status: 'in_progress'}]});
  });
  assert.equal(calls, 1);
  assert.equal(result.dispatched, false);
});

test('missing credentials and rejected dispatches fail visibly', async () => {
  await assert.rejects(dispatch({}), /missing/);
  let calls = 0;
  await assert.rejects(dispatch({GITHUB_TOKEN: 'test-only'}, async () => {
    calls++;
    return calls === 1 ? Response.json({workflow_runs: []}) : new Response(null, {status: 403});
  }), /HTTP 403/);
  assert.equal(calls, 2);
});

test('HTTP visits cannot trigger work', async () => {
  assert.equal(worker.fetch().status, 404);
});
