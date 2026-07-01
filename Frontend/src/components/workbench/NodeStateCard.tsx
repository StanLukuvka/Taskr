// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { formatCurrencyCents } from '@/lib/formatters';
import { formatDate } from '@/lib/utils';
import { nodeStatusClasses as statusClasses } from '@/lib/status-styles';
import type { NodeState } from '@/types/taskr';

function summarize(nodeState: NodeState): string {
  if (nodeState.error_message) {
    return nodeState.error_message;
  }
  if (nodeState.output != null) {
    return 'Output captured';
  }
  if (nodeState.raw_output != null) {
    return 'Raw output available';
  }
  if (nodeState.external_ref) {
    return `External ref ${nodeState.external_ref}`;
  }
  return 'Awaiting execution';
}

interface NodeStateCardProps {
  children?: ReactNode;
  nodeState: NodeState;
  onSelect: () => void;
  onRestart?: (nodeId: string) => void;
  onRetryNode?: (nodeStateId: string) => void;
  selected: boolean;
}

export function NodeStateCard({ children, nodeState, onSelect, onRestart, onRetryNode, selected }: NodeStateCardProps) {
  return (
    <article
      className={[
        'border p-4 transition-colors',
        selected
          ? 'border-primary/50 bg-primary/10 shadow-[0_0_0_1px_rgba(255,191,0,0.2)]'
          : 'border-border/70 bg-black/10 hover:border-primary/30 hover:bg-black/15',
      ].join(' ')}
    >
      <button className="w-full text-left" type="button" onClick={onSelect}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{nodeState.node_kind ?? 'node'}</p>
            <h3 className="mt-1 text-base font-semibold text-foreground">
              {nodeState.node_title ?? nodeState.node_id}
            </h3>
          </div>
          <span className={`inline-flex px-2.5 py-1 text-xs font-medium ring-1 ${statusClasses[nodeState.status]}`}>
            {nodeState.status}
          </span>
        </div>

        <div className="mt-4 grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Binding</div>
            <div className="mt-1 text-foreground/85">{nodeState.binding_id ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Attempt</div>
            <div className="mt-1 text-foreground/85">{nodeState.attempt}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Updated</div>
            <div className="mt-1 text-foreground/85">{formatDate(nodeState.updated_at)}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Cost</div>
            <div className="mt-1 text-foreground/85">{formatCurrencyCents(nodeState.cost_cents ?? 0)}</div>
          </div>
          <div className="md:col-span-2">
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Summary</div>
            <div className="mt-1 text-foreground/85">{summarize(nodeState)}</div>
          </div>
        </div>
      </button>
      {onRestart && onRetryNode && nodeState.node_kind !== 'foreach' && !nodeState.loop_iteration_id ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRestart(nodeState.node_id)}
          >
            Restart from here
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRetryNode(nodeState.id)}
          >
            Retry node
          </Button>
        </div>
      ) : null}
      {children ? <div className="mt-4 border-t border-border/70 pt-4">{children}</div> : null}
    </article>
  );
}
