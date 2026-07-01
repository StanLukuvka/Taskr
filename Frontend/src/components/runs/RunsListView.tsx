// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';
import { useCreateRun, useRunList } from '@/hooks/use-taskr';
import { runStatusClasses as statusClasses } from '@/lib/status-styles';
import type { JsonValue, RunListItem } from '@/types/taskr';
import { BudgetBadge } from '@/components/runs/BudgetBadge';

function sortRuns(runs: RunListItem[]) {
  return [...runs].sort((left, right) => (right.created_at ?? '').localeCompare(left.created_at ?? ''));
}

export function RunsListView() {
  const navigate = useNavigate();
  const runList = useRunList();
  const createRunMutation = useCreateRun();
  const [flowSlug, setFlowSlug] = useState('soda-comparison');
  const [contextText, setContextText] = useState('{}');
  const [formError, setFormError] = useState<string | null>(null);

  const runs = useMemo(() => sortRuns(runList.data ?? []), [runList.data]);

  async function handleCreateRun() {
    setFormError(null);

    let context: Record<string, JsonValue> | undefined;
    try {
      const parsed = JSON.parse(contextText) as JsonValue;
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        context = parsed as Record<string, JsonValue>;
      } else {
        setFormError('Context JSON must be an object.');
        return;
      }
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON payload.');
      return;
    }

    try {
      const run = await createRunMutation.mutateAsync({
        flow_slug: flowSlug,
        context,
      });
      navigate(`/runs/${run.id}`);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Failed to create run.');
    }
  }

  return (
    <div className="space-y-4">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Runs</p>
              <h1 className="mt-1 text-4xl font-bold uppercase tracking-[0.1em] text-accent">Execution workbench</h1>
            </div>
            <Button variant="ghost" onClick={() => runList.refetch()}>
              Refresh
            </Button>
          </div>

          {runList.isLoading ? (
            <div className="border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              Loading runs…
            </div>
          ) : runList.isError ? (
            <div className="border border-rose-400/30 bg-rose-500/10 px-4 py-8 text-sm text-rose-200">
              <p>Failed to load runs.</p>
              <p className="mt-1 text-xs text-rose-200/70">
                {runList.error instanceof Error ? runList.error.message : 'Unknown error.'}
              </p>
              <Button variant="secondary" className="mt-1" onClick={() => runList.refetch()}>
                Retry
              </Button>
            </div>
          ) : runs.length === 0 ? (
            <div className="border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              No runs yet. Create one from the panel on the right.
            </div>
          ) : (
            <div className="overflow-hidden border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-black/10 text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Run</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Budget</th>
                    <th className="px-3 py-2">Created</th>
                    <th className="px-3 py-2">Flow version</th>
                    <th className="px-3 py-2 text-right">Open</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {runs.map((run) => (
                    <tr key={run.id} className="bg-black/5">
                      <td className="px-3 py-2 align-top">
                        <div className="font-medium text-foreground">{run.id}</div>
                        <div className="text-xs text-muted-foreground">{run.flow_id}</div>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <span className={`inline-flex px-2.5 py-1 text-xs font-medium ring-1 ${statusClasses[run.status]}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <BudgetBadge run={run} />
                      </td>
                      <td className="px-3 py-2 align-top text-muted-foreground">{formatDate(run.created_at)}</td>
                      <td className="px-3 py-2 align-top text-muted-foreground">{run.flow_version_id}</td>
                      <td className="px-3 py-2 text-right align-top">
                        <Button variant="outline" size="sm" onClick={() => navigate(`/runs/${run.id}`)}>
                          Open workbench
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Create run</p>
          <h2 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">Seed a demo execution</h2>
          <div className="mt-4 space-y-4">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-foreground">Flow slug</span>
              <select
                className="w-full border border-border/70 bg-background/80 px-3 py-2.5 text-sm"
                value={flowSlug}
                onChange={(event) => setFlowSlug(event.target.value)}
              >
                <option value="soda-comparison">soda-comparison</option>
                <option value="product-infographic">product-infographic</option>
                <option value="frontend-demo">frontend-demo</option>
              </select>
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-foreground">Context JSON</span>
              <textarea
                className="min-h-48 w-full border border-border/70 bg-background/80 px-3 py-2.5 font-mono text-xs leading-6"
                value={contextText}
                onChange={(event) => setContextText(event.target.value)}
              />
            </label>
            {formError ? <p className="text-sm text-rose-300">{formError}</p> : null}
            <Button size="lg" className="w-full" onClick={() => void handleCreateRun()}>
              {createRunMutation.isPending ? 'Creating run…' : 'Create and open'}
            </Button>
          </div>
        </aside>
      </section>
    </div>
  );
}
