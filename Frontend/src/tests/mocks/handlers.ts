import { http, HttpResponse } from 'msw';
import { apiBinding, bindings, hermesBinding } from '@/tests/fixtures/bindings';
import { activeFlow, flows } from '@/tests/fixtures/flows';
import { flowVersion } from '@/tests/fixtures/flowVersion';
import {
  baseRun,
  makeRun,
  makeRunItem,
  makeRunWithStatus,
  runProgression,
} from '@/tests/fixtures/runs';
import type { CreateRunRequest, Run } from '@/types/taskr';

/**
 * Mutable run store so handlers can track POST-created runs and
 * simulate progression across successive GET /runs/:runId calls.
 */
let createdRuns: Record<string, Run> = {};
let runPollIndex = 0;

export function resetMockStore() {
  createdRuns = {};
  runPollIndex = 0;
}

function resolveRun(runId: string): Run | undefined {
  if (runId === baseRun.id) {
    const run = runProgression[runPollIndex] ?? runProgression[runProgression.length - 1];
    return run;
  }
  return createdRuns[runId];
}

export const handlers = [
  // GET /flows → FlowSummary[]
  http.get('*/flows', () => {
    return HttpResponse.json(flows);
  }),

  // GET /flows/:slug → FlowSummary
  http.get('*/flows/:slug', ({ params }) => {
    const slug = params.slug as string;
    const flow = flows.find((f) => f.slug === slug);
    if (!flow) {
      return HttpResponse.json({ detail: `Flow '${slug}' not found` }, { status: 404 });
    }
    return HttpResponse.json(flow);
  }),

  // GET /flow_versions/:id → FlowVersion
  http.get('*/flow_versions/:id', ({ params }) => {
    const id = params.id as string;
    if (id !== flowVersion.id) {
      return HttpResponse.json({ detail: `Flow version '${id}' not found` }, { status: 404 });
    }
    return HttpResponse.json(flowVersion);
  }),

  // POST /runs → Run
  http.post('*/runs', async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as CreateRunRequest;
    const run = makeRun({
      id: `run-${Date.now()}`,
      status: 'pending',
      flow_id: activeFlow.id,
      flow_version_id: activeFlow.active_flow_version_id ?? 'fv-1',
      context: body.context ?? {},
    });
    createdRuns[run.id] = run;
    return HttpResponse.json(run);
  }),

  // GET /runs → RunListItem[]
  http.get('*/runs', () => {
    const items = [
      makeRunItem(),
      ...Object.values(createdRuns).map((r) =>
        makeRunItem({
          id: r.id,
          status: r.status,
          flow_id: r.flow_id,
          flow_version_id: r.flow_version_id,
          context: r.context,
          total_cost_cents: r.total_cost_cents,
          created_at: r.created_at,
          started_at: r.started_at,
          finished_at: r.finished_at,
        }),
      ),
    ];
    return HttpResponse.json(items);
  }),

  // GET /runs/:runId → Run (progression for the base run)
  http.get('*/runs/:runId', ({ params }) => {
    const runId = params.runId as string;
    const run = resolveRun(runId);
    if (!run) {
      return HttpResponse.json({ detail: `Run '${runId}' not found` }, { status: 404 });
    }
    // Advance poll index for the base run to simulate progression
    if (runId === baseRun.id && runPollIndex < runProgression.length - 1) {
      runPollIndex++;
    }
    return HttpResponse.json(run);
  }),

  // POST /runs/:runId/tick → Run
  http.post('*/runs/:runId/tick', ({ params }) => {
    const runId = params.runId as string;
    const run = resolveRun(runId);
    if (!run) {
      return HttpResponse.json({ detail: `Run '${runId}' not found` }, { status: 404 });
    }
    const ticked = makeRunWithStatus('running', {
      ...run,
      status: 'running',
      started_at: run.started_at ?? '2026-06-30T10:00:05Z',
    });
    return HttpResponse.json(ticked);
  }),

  // POST /runs/:runId/cancel → RunActionResponse
  http.post('*/runs/:runId/cancel', ({ params }) => {
    const runId = params.runId as string;
    return HttpResponse.json({ status: 'cancelled', run_id: runId });
  }),

  // POST /runs/:runId/retry → Run (new run with different id)
  http.post('*/runs/:runId/retry', ({ params }) => {
    const runId = params.runId as string;
    const newRun = makeRun({
      id: `run-retry-${runId}`,
      status: 'pending',
    });
    createdRuns[newRun.id] = newRun;
    return HttpResponse.json(newRun);
  }),

  // POST /runs/:runId/restart_from → RestartFromResponse
  http.post('*/runs/:runId/restart_from', async ({ params, request }) => {
    const runId = params.runId as string;
    const body = (await request.json().catch(() => ({}))) as { node_id?: string };
    const newRun = makeRun({
      id: `run-restart-${runId}-${body.node_id ?? 'unknown'}`,
      status: 'pending',
    });
    createdRuns[newRun.id] = newRun;
    return HttpResponse.json({ ...newRun, source_run_id: runId });
  }),

  // POST /runs/:runId/node-states/:nodeStateId/retry → RetryNodeResponse
  http.post('*/runs/:runId/node-states/:nodeStateId/retry', ({ params }) => {
    const runId = params.runId as string;
    const nodeStateId = params.nodeStateId as string;
    return HttpResponse.json({
      status: 'retried',
      node_state_id: nodeStateId,
      run_id: runId,
    });
  }),

  // DELETE /runs/:runId → 204
  http.delete('*/runs/:runId', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // GET /bindings → Binding[]
  http.get('*/bindings', () => {
    return HttpResponse.json(bindings);
  }),

  // GET /bindings/:integrationId → Binding
  http.get('*/bindings/:integrationId', ({ params }) => {
    const id = params.integrationId as string;
    if (id === apiBinding.id) return HttpResponse.json(apiBinding);
    if (id === hermesBinding.id) return HttpResponse.json(hermesBinding);
    return HttpResponse.json({ detail: `Binding '${id}' not found` }, { status: 404 });
  }),
];

/** A 500 error handler variant for testing error states. */
export const errorHandlers = [
  http.get('*/runs/:runId', () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 },
    );
  }),
];

