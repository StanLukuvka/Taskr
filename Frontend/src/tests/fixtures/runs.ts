import type { NodeState, Run, RunListItem, RunStatus } from '@/types/taskr';

const baseRun: Run = {
  id: 'run-1',
  status: 'pending',
  flow_id: 'flow-1',
  flow_version_id: 'fv-1',
  context: { retailer: 'woolworths', category: 'soda' },
  cost_cents: 0,
  total_cost_cents: 0,
  failure_summary: null,
  created_at: '2026-06-30T10:00:00Z',
  started_at: null,
  finished_at: null,
  node_states: [
    {
      id: 'ns-1',
      run_id: 'run-1',
      node_id: 'node-api-1',
      node_title: 'Fetch prices',
      node_kind: 'api',
      loop_iteration_id: null,
      status: 'pending',
      binding_id: 'bind-api-1',
      binding_snapshot: null,
      external_ref: null,
      input: null,
      raw_output: null,
      output: null,
      cost_cents: 0,
      error_code: null,
      error_message: null,
      attempt: 0,
      created_at: '2026-06-30T10:00:00Z',
      started_at: null,
      finished_at: null,
      updated_at: '2026-06-30T10:00:00Z',
    },
    {
      id: 'ns-2',
      run_id: 'run-1',
      node_id: 'node-foreach-1',
      node_title: 'Loop over retailers',
      node_kind: 'foreach',
      loop_iteration_id: null,
      status: 'pending',
      binding_id: null,
      binding_snapshot: null,
      external_ref: null,
      input: null,
      raw_output: null,
      output: null,
      cost_cents: 0,
      error_code: null,
      error_message: null,
      attempt: 0,
      created_at: '2026-06-30T10:00:00Z',
      started_at: null,
      finished_at: null,
      updated_at: '2026-06-30T10:00:00Z',
    },
  ],
};

export function makeRun(overrides: Partial<Run> = {}): Run {
  return { ...baseRun, ...overrides };
}

export function makeRunWithStatus(status: RunStatus, overrides: Partial<Run> = {}): Run {
  return makeRun({ status, ...overrides });
}

export function makeRunItem(overrides: Partial<RunListItem> = {}): RunListItem {
  return {
    id: baseRun.id,
    status: baseRun.status,
    flow_id: baseRun.flow_id,
    flow_version_id: baseRun.flow_version_id,
    total_cost_cents: baseRun.total_cost_cents,
    created_at: baseRun.created_at,
    started_at: baseRun.started_at,
    finished_at: baseRun.finished_at,
    ...overrides,
  };
}

export function makeNodeState(overrides: Partial<NodeState> = {}): NodeState {
  return { ...baseRun.node_states[0], ...overrides };
}

/**
 * Returns a sequence of Run objects simulating poll_run.sh progression.
 * Each call to the mock GET /runs/:runId handler pops the next state.
 */
export const runProgression: Run[] = [
  makeRunWithStatus('pending'),
  makeRunWithStatus('running', {
    started_at: '2026-06-30T10:00:05Z',
    node_states: [
      makeNodeState({ id: 'ns-1', status: 'completed', output: { price: 3.5 } }),
      makeNodeState({ id: 'ns-2', status: 'running' }),
    ],
  }),
  makeRunWithStatus('completed', {
    finished_at: '2026-06-30T10:00:30Z',
    total_cost_cents: 42,
    node_states: [
      makeNodeState({ id: 'ns-1', status: 'completed', output: { price: 3.5 } }),
      makeNodeState({ id: 'ns-2', status: 'completed', output: { verdict: 'ok' } }),
    ],
  }),
];

export { baseRun };
