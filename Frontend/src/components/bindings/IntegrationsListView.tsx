// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import { Link, useSearchParams } from 'react-router';
import { useBindings } from '@/hooks/use-taskr';
import { formatDate } from '@/lib/utils';
import type { Binding } from '@/types/taskr';

function getPageCopy(kind: string | null): { eyebrow: string; title: string; description: string } {
  if (kind === 'hermes') {
    return {
      eyebrow: 'Agent integrations',
      title: 'Hermes agent integrations',
      description: 'Read-only Hermes task dispatch configs. This replaces the mockup Agent page.',
    };
  }

  if (kind === 'api') {
    return {
      eyebrow: 'API integrations',
      title: 'API integrations',
      description: 'Read-only HTTP integration configs. This replaces the mockup Integrations page.',
    };
  }

  return {
    eyebrow: 'Integrations',
    title: 'All integrations',
    description: 'Inspect every stored integration and open its config detail page.',
  };
}

function matchesFilter(binding: Binding, kind: string | null): boolean {
  return kind ? binding.kind === kind : true;
}

export function IntegrationsListView() {
  const [searchParams] = useSearchParams();
  const kind = searchParams.get('kind');
  const { data, isLoading, error } = useBindings();
  const copy = getPageCopy(kind);
  const filtered = data?.filter((binding) => matchesFilter(binding, kind)) ?? [];

  if (isLoading) {
    return <div className="border border-border bg-card p-4 text-sm text-muted-foreground">Loading integrations…</div>;
  }

  if (error) {
    return <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">Failed to load integrations.</div>;
  }

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">{copy.eyebrow}</p>
        <h2 className="text-4xl font-bold uppercase tracking-[0.1em] text-accent">{copy.title}</h2>
        <p className="max-w-3xl text-sm text-muted-foreground">{copy.description}</p>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="border border-border bg-card px-3 py-2 text-muted-foreground hover:text-foreground" to="/integrations">
          All
        </Link>
        <Link className="border border-border bg-card px-3 py-2 text-muted-foreground hover:text-foreground" to="/integrations?kind=hermes">
          Agent
        </Link>
        <Link className="border border-border bg-card px-3 py-2 text-muted-foreground hover:text-foreground" to="/integrations?kind=api">
          Integrations
        </Link>
      </div>

      <div className="overflow-hidden border border-border bg-card">
        <table className="min-w-full divide-y divide-border text-left text-sm">
          <thead className="bg-black/10 text-xs uppercase tracking-[0.24em] text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Enabled</th>
              <th className="px-3 py-2">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((binding) => (
              <tr key={binding.id} className="align-top text-foreground">
                <td className="px-3 py-2">
                  <Link className="font-semibold text-foreground underline-offset-4 hover:underline" to={`/integrations/${binding.id}`}>
                    {binding.display_title}
                  </Link>
                  <div className="mt-1 font-mono text-xs text-muted-foreground">{binding.id}</div>
                </td>
                <td className="px-3 py-2 uppercase tracking-[0.2em] text-accent">{binding.kind}</td>
                <td className="px-3 py-2 text-muted-foreground">{binding.is_enabled ? 'Enabled' : 'Disabled'}</td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(binding.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {!filtered.length ? (
          <div className="p-4 text-sm text-muted-foreground">No integrations matched this filter.</div>
        ) : null}
      </div>
    </section>
  );
}
