import type { FlowSummary } from '@/types/taskr';

export const activeFlow: FlowSummary = {
  id: 'flow-1',
  title: 'Soda Comparison',
  slug: 'soda-comparison',
  description: 'Compare soda prices across retailers',
  created_at: '2026-06-10T03:00:00Z',
  updated_at: '2026-06-25T08:00:00Z',
  active_flow_version_id: 'fv-1',
  active_flow_version_status: 'active',
};

export const inactiveFlow: FlowSummary = {
  id: 'flow-2',
  title: 'Draft Only Flow',
  slug: 'draft-only',
  description: 'Has no published version yet',
  created_at: '2026-06-15T03:00:00Z',
  updated_at: '2026-06-15T03:00:00Z',
  active_flow_version_id: null,
  active_flow_version_status: null,
};

export const flows: FlowSummary[] = [activeFlow, inactiveFlow];
