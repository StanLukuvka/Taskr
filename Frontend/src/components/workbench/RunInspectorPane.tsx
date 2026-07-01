// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import { formatCurrencyCents } from '@/lib/formatters';
import { formatDate } from '@/lib/utils';
import { useBudgetSettings } from '@/hooks/use-budget-settings';
import type {
  FlowNode,
  ForeachIterationView,
  ForeachRuntimeView,
  InspectorTab,
  NodeState,
} from '@/types/taskr';
import { NodeStateJsonPanel } from './NodeStateJsonPanel';

const tabs: { id: InspectorTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'input', label: 'Input' },
  { id: 'output', label: 'Output' },
  { id: 'native', label: 'Native state' },
  { id: 'loop', label: 'Loop context' },
  { id: 'budget', label: 'Budget' },
];

interface RunInspectorPaneProps {
  activeTab: InspectorTab;
  flowNode: FlowNode | null;
  foreachRuntime: ForeachRuntimeView | null;
  onSelectTab: (tab: InspectorTab) => void;
  selectedIterationId: string | null;
  selectedNodeState: NodeState | null;
  nodeStates: NodeState[];
  totalCostCents: number;
}

function loopSummary(
  foreachRuntime: ForeachRuntimeView | null,
  selectedIterationId: string | null
): ForeachIterationView | null {
  if (!foreachRuntime) {
    return null;
  }
  if (!selectedIterationId) {
    return foreachRuntime.iterations[0] ?? null;
  }
  return (
    foreachRuntime.iterations.find((iteration) => iteration.iterationId === selectedIterationId) ?? null
  );
}

export function RunInspectorPane({
  activeTab,
  flowNode,
  foreachRuntime,
  onSelectTab,
  selectedIterationId,
  selectedNodeState,
  nodeStates,
  totalCostCents,
}: RunInspectorPaneProps) {
  // The Budget tab is a run-level view — show it even when no node is selected.
  if (!selectedNodeState && activeTab !== 'budget') {
    return (
      <section className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
        <div className="mb-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={[
                'border px-3 py-1.5 text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-accent/50 bg-accent/15 text-accent'
                  : 'border-border/70 bg-black/10 text-foreground/85 hover:border-accent/30',
              ].join(' ')}
              type="button"
              onClick={() => onSelectTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
          Select a node state to inspect its runtime payloads.
        </div>
      </section>
    );
  }

  const selectedIteration = loopSummary(foreachRuntime, selectedIterationId);

  return (
    <section className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
      {selectedNodeState ? (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Inspector</p>
            <h2 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">
              {selectedNodeState.node_title ?? selectedNodeState.node_id}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {selectedNodeState.node_kind ?? 'node'} · {selectedNodeState.status}
            </p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <div>{selectedNodeState.id}</div>
            {selectedNodeState.loop_iteration_id ? <div>{selectedNodeState.loop_iteration_id}</div> : null}
          </div>
        </div>
      ) : (
        <div className="mb-4">
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Inspector</p>
          <h2 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">
            Budget breakdown
          </h2>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {tabs
          .filter((tab) => tab.id !== 'loop' || !!foreachRuntime)
          .map((tab) => (
            <button
              key={tab.id}
              className={[
                'border px-3 py-1.5 text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-accent/50 bg-accent/15 text-accent'
                  : 'border-border/70 bg-black/10 text-foreground/85 hover:border-accent/30',
              ].join(' ')}
              type="button"
              onClick={() => onSelectTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
      </div>

      {activeTab === 'overview' ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <InspectorStat label="Binding" value={selectedNodeState.binding_id ?? '—'} />
          <InspectorStat label="Attempt" value={String(selectedNodeState.attempt)} />
          <InspectorStat label="External ref" value={selectedNodeState.external_ref ?? '—'} />
          <InspectorStat label="Created" value={formatDate(selectedNodeState.created_at)} />
          <InspectorStat label="Started" value={formatDate(selectedNodeState.started_at)} />
          <InspectorStat label="Finished" value={formatDate(selectedNodeState.finished_at)} />
          <InspectorStat label="Flow node" value={flowNode?.id ?? selectedNodeState.node_id} />
          <InspectorStat label="Failure policy" value={flowNode?.failure_policy ?? '—'} />
          <InspectorStat label="Items path" value={flowNode?.items_path ?? '—'} />
          {selectedNodeState.error_message ? (
            <div className="border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100 md:col-span-2 xl:col-span-3">
              <div className="text-xs uppercase tracking-[0.2em] text-rose-200/80">Error</div>
              <div className="mt-1">{selectedNodeState.error_message}</div>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === 'input' ? (
        <NodeStateJsonPanel emptyLabel="No resolved input recorded for this node state." value={selectedNodeState.input} />
      ) : null}

      {activeTab === 'output' ? (
        <NodeStateJsonPanel
          emptyLabel="No output payload is available yet for this node state."
          value={selectedNodeState.output ?? selectedNodeState.raw_output}
        />
      ) : null}

      {activeTab === 'native' ? (
        <div className="space-y-3">
          <div>
            <div className="mb-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">Binding snapshot</div>
            <NodeStateJsonPanel emptyLabel="No binding snapshot recorded." value={selectedNodeState.binding_snapshot} />
          </div>
          <div>
            <div className="mb-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">Raw output</div>
            <NodeStateJsonPanel emptyLabel="No raw integration payload is available yet." value={selectedNodeState.raw_output} />
          </div>
        </div>
      ) : null}

      {activeTab === 'loop' ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <InspectorStat
              label="Iterations"
              value={String(foreachRuntime?.iterations.length ?? 0)}
            />
            <InspectorStat label="Selected iteration" value={selectedIteration?.iterationId ?? '—'} />
            <InspectorStat
              label="Child nodes"
              value={String(foreachRuntime?.childNodeIds.length ?? 0)}
            />
          </div>
          {selectedIteration ? (
            <div className="border border-border/70 bg-black/10 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Iteration detail</div>
              <div className="mt-1 text-sm text-foreground">{selectedIteration.iterationId}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedIteration.childStates.map((childState) => (
                  <span
                    key={childState.id}
                    className="border border-border/70 bg-black/10 px-3 py-1 text-xs text-foreground/85"
                  >
                    {childState.node_title ?? childState.node_id} · {childState.status}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="border border-dashed border-border/70 px-4 py-6 text-sm text-muted-foreground">
              No foreach iterations have been materialized yet.
            </div>
          )}
        </div>
      ) : null}

      {activeTab === 'budget' ? <BudgetBreakdown nodeStates={nodeStates} totalCostCents={totalCostCents} /> : null}
    </section>
  );
}

interface InspectorStatProps {
  label: string;
  value: string;
}

function InspectorStat({ label, value }: InspectorStatProps) {
  return (
    <div className="border border-border/70 bg-black/10 p-4">
      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm text-foreground/90">{value}</div>
    </div>
  );
}

interface BudgetBreakdownProps {
  nodeStates: NodeState[];
  totalCostCents: number;
}

function BudgetBreakdown({ nodeStates, totalCostCents }: BudgetBreakdownProps) {
  const { budgetCents, threshold, label } = useBudgetSettings();
  const spent = totalCostCents ?? 0;
  const cap = budgetCents != null && budgetCents > 0 ? budgetCents : null;

  // Aggregate per-node costs (a node may have multiple states if foreach).
  const perNode = new Map<string, { title: string; cost: number }>();
  for (const state of nodeStates) {
    const existing = perNode.get(state.node_id);
    const cost = state.cost_cents ?? 0;
    if (existing) {
      existing.cost += cost;
    } else {
      perNode.set(state.node_id, {
        title: state.node_title ?? state.node_id,
        cost,
      });
    }
  }

  const rows = [...perNode.entries()]
    .map(([nodeId, info]) => ({ nodeId, ...info }))
    .sort((a, b) => b.cost - a.cost);

  const computedTotal = rows.reduce((sum, r) => sum + r.cost, 0);
  const remaining = cap != null ? Math.max(0, cap - spent) : null;
  const exhausted = remaining != null && remaining <= 0;
  const pct = cap != null && cap > 0 ? Math.min(100, (spent / cap) * 100) : 0;
  const nearThreshold = !exhausted && pct >= threshold * 100;
  const barColor = exhausted
    ? 'bg-rose-500/80'
    : nearThreshold
      ? 'bg-amber-500/80'
      : 'bg-accent/80';
  const status = cap == null
    ? 'No cap set'
    : exhausted
      ? 'Exhausted'
      : nearThreshold
        ? 'Near threshold'
        : 'Under budget';

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <InspectorStat label="Run total" value={formatCurrencyCents(spent)} />
        <InspectorStat label="Cap" value={cap != null ? formatCurrencyCents(cap) : '—'} />
        <InspectorStat label="Remaining" value={remaining != null ? formatCurrencyCents(remaining) : '—'} />
      </div>

      {cap != null ? (
        <div>
          <div className="h-2 w-full bg-black/30">
            <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>{pct.toFixed(0)}%</span>
            <span className={exhausted ? 'text-rose-300' : nearThreshold ? 'text-amber-300' : ''}>
              {status} · {label}
            </span>
          </div>
        </div>
      ) : null}

      <div>
        <div className="mb-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Per-node cost ({rows.length} nodes)
        </div>
        {rows.length === 0 ? (
          <div className="border border-dashed border-border/70 px-4 py-6 text-sm text-muted-foreground">
            No node cost data yet.
          </div>
        ) : (
          <table className="min-w-full divide-y divide-border/70 text-sm">
            <thead className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Node</th>
                <th className="px-3 py-2 text-right">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {rows.map((row) => (
                <tr key={row.nodeId} className="bg-black/5">
                  <td className="px-3 py-2 text-foreground/90">{row.title}</td>
                  <td className="px-3 py-2 text-right font-mono text-foreground/90">
                    {formatCurrencyCents(row.cost)}
                  </td>
                </tr>
              ))}
              <tr className="bg-black/10">
                <td className="px-3 py-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">Sum</td>
                <td className="px-3 py-2 text-right font-mono text-sm font-semibold text-foreground">
                  {formatCurrencyCents(computedTotal)}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
