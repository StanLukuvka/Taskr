// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m2-flows-workbench.md
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useFlowBySlug, useFlowVersion, useCreateRun, useRunsForFlow, useRunList } from '@/hooks/use-taskr';
import { NodeTree } from '@/components/flows/NodeTree';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';
import { runStatusClasses } from '@/lib/status-styles';
import { formatCurrencyCents } from '@/lib/formatters';
import type { JsonValue } from '@/types/taskr';

export function FlowDetailView() {
  const { slug } = useParams();
  const navigate = useNavigate();

  const {
    data: flowSummary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useFlowBySlug(slug);

  const activeVersionId = flowSummary?.active_flow_version_id ?? undefined;
  const {
    data: flowVersion,
    isLoading: versionLoading,
    error: versionError,
  } = useFlowVersion(activeVersionId);

  const createRunMutation = useCreateRun();
  const runsForFlow = useRunsForFlow(flowSummary?.id);
  const runListQuery = useRunList();

  const [contextOpen, setContextOpen] = useState(false);
  const [contextText, setContextText] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  /* ---------- loading / error: flow summary ---------- */
  if (summaryLoading) {
    return <div className="border border-border bg-card p-4 text-sm text-muted-foreground">Loading flow…</div>;
  }

  if (summaryError || !flowSummary) {
    return <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">Failed to load flow.</div>;
  }

  const hasActiveVersion = Boolean(flowSummary.active_flow_version_id);
  const sortedRuns = [...runsForFlow].sort(
    (left, right) => (right.created_at ?? '').localeCompare(left.created_at ?? ''),
  );

  async function handleRunFlow() {
    setFormError(null);

    if (!slug) {
      setFormError('Flow slug unavailable — cannot start run.');
      return;
    }

    let context: Record<string, JsonValue> | undefined;
    const trimmed = contextText.trim();
    if (trimmed) {
      try {
        const parsed = JSON.parse(trimmed) as JsonValue;
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          context = parsed as Record<string, JsonValue>;
        } else {
          setFormError('Context JSON must be an object.');
          return;
        }
      } catch (parseError) {
        setFormError(parseError instanceof Error ? parseError.message : 'Invalid JSON payload.');
        return;
      }
    } else {
      context = {};
    }

    try {
      const run = await createRunMutation.mutateAsync({ flow_slug: slug, context });
      navigate(`/runs/${run.id}`);
    } catch (runError) {
      setFormError(runError instanceof Error ? runError.message : 'Failed to create run.');
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Link className="underline-offset-4 hover:text-foreground hover:underline" to="/flows">
          Flows
        </Link>
        <span>/</span>
        <span className="text-foreground">{flowSummary.title}</span>
      </div>

      <div className="border border-border bg-card p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Flow</p>
            <div>
              <h2 className="text-4xl font-bold uppercase tracking-[0.1em] text-accent">{flowSummary.title}</h2>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                {flowSummary.description || 'No description provided.'}
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{flowSummary.slug}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100">
              {flowSummary.active_flow_version_status ?? 'no version'}
            </span>
            {flowVersion ? (
              <span className="border border-accent/40 bg-accent/10 px-3 py-2 text-sm text-accent">
                version {flowVersion.version}
              </span>
            ) : null}
          </div>
        </div>

        <div className="mt-4 space-y-3 border-t border-border pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="lg"
              onClick={() => void handleRunFlow()}
              disabled={createRunMutation.isPending || !hasActiveVersion}
            >
              {createRunMutation.isPending ? 'Starting run…' : 'Run flow'}
            </Button>
            <Button variant="outline" size="lg" onClick={() => setContextOpen((open) => !open)}>
              {contextOpen ? 'Hide context' : 'Add context JSON'}
            </Button>
          </div>

          {contextOpen ? (
            <div className="space-y-2">
              <label className="block space-y-1">
                <span className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
                  Run context (optional, defaults to {'{}'})
                </span>
                <textarea
                  className="min-h-32 w-full border border-border bg-background/80 px-3 py-2 font-mono text-xs leading-6"
                  placeholder='{"key":"value"}'
                  value={contextText}
                  onChange={(event) => setContextText(event.target.value)}
                />
              </label>
              {formError ? <p className="text-sm text-rose-300">{formError}</p> : null}
            </div>
          ) : (
            formError ? <p className="text-sm text-rose-300">{formError}</p> : null
          )}
        </div>
      </div>

      {/* ---------- version / node tree ---------- */}
      {!hasActiveVersion ? (
        <div className="border border-border bg-card p-4 text-sm text-muted-foreground">
          This flow has no active version. Node tree is unavailable until a version is activated.
        </div>
      ) : versionLoading ? (
        <div className="border border-border bg-card p-4 text-sm text-muted-foreground">Loading flow version…</div>
      ) : versionError || !flowVersion ? (
        <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">
          Failed to load flow version.
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Node tree</p>
            <h3 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">Nested execution structure</h3>
          </div>
          <NodeTree nodes={flowVersion.nodes} />
        </div>
      )}

      {/* ---------- run history ---------- */}
      <div className="space-y-3">
        <div>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Run history</p>
          <h3 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">Prior executions</h3>
        </div>
        {runListQuery.isLoading ? (
          <div className="border border-border bg-card p-4 text-sm text-muted-foreground">Loading run history…</div>
        ) : runListQuery.isError ? (
          <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            Failed to load run history.
          </div>
        ) : sortedRuns.length === 0 ? (
          <div className="border border-border bg-card p-4 text-sm text-muted-foreground">
            No runs for this flow yet.
          </div>
        ) : (
          <div className="overflow-hidden border border-border bg-card">
            <table className="min-w-full divide-y divide-border text-left text-sm">
              <thead className="bg-black/10 text-xs uppercase tracking-[0.24em] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Run</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Started</th>
                  <th className="px-3 py-2">Finished</th>
                  <th className="px-3 py-2 text-right">Total cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sortedRuns.map((run) => (
                  <tr key={run.id} className="bg-black/5">
                    <td className="px-3 py-2 align-top">
                      <Link className="font-medium text-foreground underline-offset-4 hover:underline" to={`/runs/${run.id}`}>
                        {run.id}
                      </Link>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <span className={`inline-flex px-2.5 py-1 text-xs font-medium ring-1 ${runStatusClasses[run.status]}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top text-muted-foreground">{formatDate(run.created_at)}</td>
                    <td className="px-3 py-2 align-top text-muted-foreground">{formatDate(run.started_at)}</td>
                    <td className="px-3 py-2 align-top text-muted-foreground">{formatDate(run.finished_at)}</td>
                    <td className="px-3 py-2 text-right align-top text-muted-foreground">{formatCurrencyCents(run.total_cost_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
