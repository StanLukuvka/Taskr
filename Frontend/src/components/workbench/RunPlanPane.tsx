// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import type { ForeachRuntimeView, NodeState } from '@/types/taskr';
import { NodeStateCard } from './NodeStateCard';

interface RunPlanPaneProps {
  foreachByNodeId: Map<string, ForeachRuntimeView>;
  onRestart?: (nodeId: string) => void;
  onRetryNode?: (nodeStateId: string) => void;
  onSelectIteration: (iterationId: string | null) => void;
  onSelectNodeState: (nodeStateId: string) => void;
  selectedIterationId: string | null;
  selectedNodeStateId: string | null;
  topLevelStates: NodeState[];
}

export function RunPlanPane({
  foreachByNodeId,
  onRestart,
  onRetryNode,
  onSelectIteration,
  onSelectNodeState,
  selectedIterationId,
  selectedNodeStateId,
  topLevelStates,
}: RunPlanPaneProps) {
  return (
    <section className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Plan</p>
          <h2 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">Node state timeline</h2>
        </div>
        <div className="text-sm text-muted-foreground">{topLevelStates.length} top-level nodes</div>
      </div>

      <div className="space-y-4">
        {topLevelStates.map((nodeState) => {
          const foreachRuntime = foreachByNodeId.get(nodeState.node_id);
          return (
            <NodeStateCard
              key={nodeState.id}
              nodeState={nodeState}
              onRestart={onRestart}
              onRetryNode={onRetryNode}
              selected={selectedNodeStateId === nodeState.id}
              onSelect={() => onSelectNodeState(nodeState.id)}
            >
              {foreachRuntime ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Foreach runtime</p>
                      <p className="text-sm text-foreground/85">
                        {foreachRuntime.iterations.length > 0
                          ? `${foreachRuntime.iterations.length} iterations materialized`
                          : 'Iterations will appear once the loop dispatches child nodes.'}
                      </p>
                    </div>
                  </div>
                  {foreachRuntime.iterations.length > 0 ? (
                    <div className="space-y-2">
                      {foreachRuntime.iterations.map((iteration) => (
                        <div
                          key={iteration.iterationId}
                          className={[
                            'border p-3',
                            selectedIterationId === iteration.iterationId
                              ? 'border-accent/50 bg-accent/10'
                              : 'border-border/70 bg-black/10',
                          ].join(' ')}
                        >
                          <button
                            className="flex w-full items-center justify-between gap-3 text-left"
                            type="button"
                            onClick={() => onSelectIteration(iteration.iterationId)}
                          >
                            <div>
                              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Iteration</div>
                              <div className="mt-1 font-medium text-foreground">{iteration.iterationId}</div>
                            </div>
                            <span className="text-xs text-muted-foreground">{iteration.status}</span>
                          </button>
                          <div className="mt-1 flex flex-wrap gap-2">
                            {iteration.childStates.map((childState) => (
                              <button
                                key={childState.id}
                                className={[
                                  'border px-3 py-1 text-xs transition-colors',
                                  selectedNodeStateId === childState.id
                                    ? 'border-accent/50 bg-accent/15 text-accent'
                                    : 'border-border/70 bg-black/10 text-foreground/85 hover:border-accent/30',
                                ].join(' ')}
                                type="button"
                                onClick={() => {
                                  onSelectIteration(iteration.iterationId);
                                  onSelectNodeState(childState.id);
                                }}
                              >
                                {childState.node_title ?? childState.node_id} · {childState.status}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </NodeStateCard>
          );
        })}
      </div>
    </section>
  );
}
