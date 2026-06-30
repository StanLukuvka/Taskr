// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m2-flows-workbench.md
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { useCreateRun, useFlows } from '@/hooks/use-taskr';
import { formatDate } from '@/lib/utils';
import type { FlowSummary } from '@/types/taskr';

export function FlowsListView() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useFlows();
  const createRunMutation = useCreateRun();
  const [pendingSlug, setPendingSlug] = useState<string | null>(null);

  async function handleRunFlow(flow: FlowSummary) {
    setPendingSlug(flow.slug);
    try {
      const run = await createRunMutation.mutateAsync({
        flow_slug: flow.slug,
        context: {},
      });
      navigate(`/runs/${run.id}`);
    } catch {
      // Mutation error is surfaced via createRunMutation.error below.
    } finally {
      setPendingSlug(null);
    }
  }

  if (isLoading) {
    return <div className="border border-white/10 bg-white/5 p-4 text-sm text-[#bdd1cd]">Loading flows…</div>;
  }

  if (error) {
    return <div className="border border-red-400/30 bg-red-950/30 p-4 text-sm text-red-100">Failed to load flows.</div>;
  }

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Flows</p>
        <h2 className="text-4xl font-bold uppercase tracking-[0.1em] text-accent">Read-only flow definitions</h2>
        <p className="max-w-3xl text-sm text-[#9eb0ad]">
          Inspect flow slugs and open a flow detail page via its slug. Flows without an
          active version are listed but cannot be opened or run.
        </p>
      </div>

      {createRunMutation.isError ? (
        <div className="border border-red-400/30 bg-red-950/30 p-3 text-sm text-red-100">
          Failed to start run:{' '}
          {createRunMutation.error instanceof Error
            ? createRunMutation.error.message
            : 'Unknown error.'}
        </div>
      ) : null}

      <div className="overflow-hidden border border-white/10 bg-[#08262b]">
        <table className="min-w-full divide-y divide-white/10 text-left text-sm">
          <thead className="bg-black/10 text-xs uppercase tracking-[0.24em] text-[#7fa19b]">
            <tr>
              <th className="px-3 py-2">Slug</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Updated</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {data?.map((flow) => {
              const hasActiveVersion = Boolean(flow.active_flow_version_id);
              const isRunningThis = pendingSlug === flow.slug;
              return (
                <tr key={flow.id} className="align-top text-[#e8f1ef]">
                  <td className="px-3 py-2 font-mono text-xs text-cyan-200">{flow.slug}</td>
                  <td className="px-3 py-2">
                    {hasActiveVersion ? (
                      <Link
                        className="font-semibold text-white underline-offset-4 hover:underline"
                        to={`/flows/${flow.slug}`}
                      >
                        {flow.title}
                      </Link>
                    ) : (
                      <span className="font-semibold text-white">
                        {flow.title} <span className="text-text-faint">(no active version)</span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-[#bdd1cd]">{flow.description}</td>
                  <td className="px-3 py-2 text-[#9eb0ad]">{formatDate(flow.updated_at ?? flow.created_at)}</td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      variant="default"
                      size="sm"
                      disabled={!hasActiveVersion || createRunMutation.isPending}
                      title={!hasActiveVersion ? 'No active version — cannot run' : undefined}
                      onClick={() => void handleRunFlow(flow)}
                    >
                      {isRunningThis ? 'Running…' : 'Run flow'}
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {!data?.length ? (
          <div className="p-4 text-sm text-[#9eb0ad]">No flows were returned by GET /flows.</div>
        ) : null}
      </div>
    </section>
  );
}
