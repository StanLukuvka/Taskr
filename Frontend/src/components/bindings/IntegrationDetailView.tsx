// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import { Link, useParams } from 'react-router';
import { useBinding } from '@/hooks/use-taskr';
import { formatDate, formatJson } from '@/lib/utils';

function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border bg-black/10 p-3">
      <dt className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm text-foreground">{value}</dd>
    </div>
  );
}

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="border border-border bg-card p-4">
      <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-accent">{title}</h3>
      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words text-xs text-foreground">{formatJson(value)}</pre>
    </div>
  );
}

export function IntegrationDetailView() {
  const { integrationId } = useParams();
  const { data: binding, isLoading, error } = useBinding(integrationId);

  if (isLoading) {
    return <div className="border border-border bg-card p-4 text-sm text-muted-foreground">Loading integration…</div>;
  }

  if (error || !binding) {
    return <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">Failed to load integration.</div>;
  }

  const backTarget = binding.kind === 'hermes' ? '/integrations?kind=hermes' : '/integrations?kind=api';

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Link className="underline-offset-4 hover:text-foreground hover:underline" to={backTarget}>
          {binding.kind === 'hermes' ? 'Agent integrations' : 'API integrations'}
        </Link>
        <span>/</span>
        <span className="text-foreground">{binding.display_title}</span>
      </div>

      <div className="border border-border bg-card p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">{binding.kind} integration</p>
            <h2 className="mt-1 text-4xl font-bold uppercase tracking-[0.1em] text-accent">{binding.display_title}</h2>
            <p className="mt-1 font-mono text-xs text-cyan-200">{binding.id}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="border border-accent/40 bg-accent/10 px-3 py-2 text-sm uppercase tracking-[0.2em] text-accent">
              {binding.kind}
            </span>
            <span className="border border-border bg-black/10 px-3 py-2 text-sm text-muted-foreground">
              {binding.is_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KeyValueRow label="Created" value={formatDate(binding.created_at)} />
        <KeyValueRow label="Updated" value={formatDate(binding.updated_at)} />
        <KeyValueRow label="Kind" value={binding.kind} />
        <KeyValueRow label="Mode" value={binding.kind === 'api' ? binding.config.completion_mode : binding.config.goal_mode ? 'goal' : 'single-turn'} />
      </div>

      {binding.kind === 'api' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <JsonPanel
            title="Request config"
            value={{
              method: binding.config.method,
              url_template: binding.config.url_template,
              auth_ref: binding.config.auth_ref,
              headers: binding.config.headers,
              request_mode: binding.config.request_mode,
            }}
          />
          <JsonPanel
            title="Polling and completion"
            value={{
              completion_mode: binding.config.completion_mode,
              external_ref_path: binding.config.external_ref_path,
              status_method: binding.config.status_method,
              status_url_template: binding.config.status_url_template,
              status_path: binding.config.status_path,
              success_values: binding.config.success_values,
              failure_values: binding.config.failure_values,
              result_path: binding.config.result_path,
            }}
          />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <JsonPanel
            title="Task templates"
            value={{
              board: binding.config.board,
              profile: binding.config.profile,
              task_title_template: binding.config.task_title_template,
              task_body_template: binding.config.task_body_template,
            }}
          />
          <JsonPanel
            title="Dispatch settings"
            value={{
              skills: binding.config.skills,
              tenant_template: binding.config.tenant_template,
              workspace_template: binding.config.workspace_template,
              goal_mode: binding.config.goal_mode,
            }}
          />
        </div>
      )}

      <div className="border border-dashed border-border/70 bg-card p-4 text-sm text-muted-foreground">
        Runtime executions and reverse links from flows are not exposed by the current backend, so this detail page stays config-only.
      </div>
    </section>
  );
}
