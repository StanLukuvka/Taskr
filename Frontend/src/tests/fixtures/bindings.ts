import type { ApiBinding, Binding, HermesBinding } from '@/types/taskr';

export const apiBinding: ApiBinding = {
  id: 'bind-api-1',
  kind: 'api',
  display_title: 'Woolworths Price API',
  is_enabled: true,
  created_at: '2026-06-20T03:00:00Z',
  updated_at: '2026-06-28T09:30:00Z',
  config: {
    method: 'GET',
    url_template: 'https://api.woolworths.example/products/{sku}',
    auth_ref: 'auth:ww',
    headers: {
      Accept: 'application/json',
      'X-Source': 'taskr',
    },
    request_mode: 'json',
    completion_mode: 'response',
    external_ref_path: 'id',
    status_method: 'GET',
    status_url_template: 'https://api.woolworths.example/jobs/{ref}',
    status_path: 'status',
    success_values: ['succeeded'],
    failure_values: ['failed'],
    result_path: 'result',
  },
};

export const hermesBinding: HermesBinding = {
  id: 'bind-hermes-1',
  kind: 'hermes',
  display_title: 'Review Agent',
  is_enabled: false,
  created_at: '2026-06-18T01:00:00Z',
  updated_at: '2026-06-27T14:00:00Z',
  config: {
    board: 'default',
    profile: 'reviewer',
    task_title_template: 'Review {flow_title}',
    task_body_template: 'Inspect run {run_id} output',
    skills: ['code-review'],
    tenant_template: null,
    workspace_template: null,
    goal_mode: true,
  },
};

export const bindings: Binding[] = [apiBinding, hermesBinding];
