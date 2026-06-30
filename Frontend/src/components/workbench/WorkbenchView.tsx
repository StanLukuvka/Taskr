// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m2-flows-workbench.md
import { useEffect, useMemo } from 'react';
import { Link, useParams } from 'react-router';
import { NodeTree } from '@/components/flows/NodeTree';
import { RunControls } from '@/components/workbench/RunControls';
import { RunInspectorPane } from '@/components/workbench/RunInspectorPane';
import { WorkbenchConsole } from '@/components/workbench/WorkbenchConsole';
import { useFlowVersion, useRun, useFlows } from '@/hooks/use-taskr';
import { useWorkbenchStore } from '@/stores/workbench-store';
import type {
  FlowNode,
  ForeachIterationView,
  ForeachRuntimeView,
  NodeState,
  NodeStateStatus,
} from '@/types/taskr';

function flattenNodes(nodes: FlowNode[]): FlowNode[] {
  return nodes.flatMap((node) => [node, ...flattenNodes(node.children)]);
}

function iterationStatus(states: NodeState[]): NodeStateStatus {
  if (states.some((state) => state.status === 'failed')) return 'failed';
  if (states.some((state) => state.status === 'running')) return 'running';
  if (states.some((state) => state.status === 'dispatching')) return 'dispatching';
  if (states.some((state) => state.status === 'ready')) return 'ready';
  if (states.some((state) => state.status === 'cancelled')) return 'cancelled';
  if (states.length > 0 && states.every((state) => state.status === 'completed')) return 'completed';
  return 'pending';
}

function sortNodeStates(states: NodeState[], nodeOrder: Map<string, number>) {
  return [...states].sort((left, right) => {
    const leftOrd = nodeOrder.get(left.node_id) ?? Number.MAX_SAFE_INTEGER;
    const rightOrd = nodeOrder.get(right.node_id) ?? Number.MAX_SAFE_INTEGER;
    if (leftOrd !== rightOrd) {
      return leftOrd - rightOrd;
    }
    return left.id.localeCompare(right.id);
  });
}

export function WorkbenchView() {
  const { runId } = useParams();
  const runQuery = useRun(runId);
  const run = runQuery.data;
  const flowVersionQuery = useFlowVersion(run?.flow_version_id);
  const flowVersion = flowVersionQuery.data;
  const flowsQuery = useFlows();
  const {
    activeTab,
    selectedIterationId,
    selectedNodeStateId,
    setActiveTab,
    setSelectedIterationId,
    setSelectedNodeStateId,
  } = useWorkbenchStore();

  const flattenedNodes = useMemo(() => flattenNodes(flowVersion?.nodes ?? []), [flowVersion?.nodes]);
  const flowNodeMap = useMemo(
    () => new Map(flattenedNodes.map((node) => [node.id, node] as const)),
    [flattenedNodes]
  );
  const nodeOrder = useMemo(
    () => new Map(flattenedNodes.map((node) => [node.id, node.ord] as const)),
    [flattenedNodes]
  );

  const topLevelStates = useMemo(
    () =>
      sortNodeStates(
        (run?.node_states ?? []).filter((nodeState) => nodeState.loop_iteration_id == null),
        nodeOrder
      ),
    [nodeOrder, run?.node_states]
  );

  const nodeStateMap = useMemo(
    () => new Map((run?.node_states ?? []).map((nodeState) => [nodeState.id, nodeState] as const)),
    [run?.node_states]
  );

  // Map node_id → node_state_id so the tree's onSelectNode(nodeId) can
  // update the store's selectedNodeStateId. Prefer top-level states; fall
  // back to any state for that node (e.g. foreach children).
  const nodeIdToStateId = useMemo(() => {
    const map = new Map<string, string>();
    for (const state of topLevelStates) {
      if (!map.has(state.node_id)) {
        map.set(state.node_id, state.id);
      }
    }
    for (const state of run?.node_states ?? []) {
      if (!map.has(state.node_id)) {
        map.set(state.node_id, state.id);
      }
    }
    return map;
  }, [topLevelStates, run?.node_states]);

  const foreachByNodeId = useMemo(() => {
    const map = new Map<string, ForeachRuntimeView>();
    const allStates = run?.node_states ?? [];

    for (const node of flattenedNodes) {
      if (node.kind !== 'foreach') {
        continue;
      }
      const childNodeIds = flattenNodes(node.children).map((childNode) => childNode.id);
      const grouped = new Map<string, NodeState[]>();
      for (const state of allStates) {
        if (!state.loop_iteration_id || !childNodeIds.includes(state.node_id)) {
          continue;
        }
        const existing = grouped.get(state.loop_iteration_id) ?? [];
        existing.push(state);
        grouped.set(state.loop_iteration_id, existing);
      }

      const iterations: ForeachIterationView[] = [...grouped.entries()]
        .map(([iterationId, childStates]) => ({
          iterationId,
          status: iterationStatus(childStates),
          childStates: sortNodeStates(childStates, nodeOrder),
        }))
        .sort((left, right) => left.iterationId.localeCompare(right.iterationId));

      map.set(node.id, {
        nodeId: node.id,
        childNodeIds,
        iterations,
      });
    }

    return map;
  }, [flattenedNodes, nodeOrder, run?.node_states]);

  const selectedNodeState = selectedNodeStateId ? nodeStateMap.get(selectedNodeStateId) ?? null : null;
  const selectedFlowNode = selectedNodeState ? flowNodeMap.get(selectedNodeState.node_id) ?? null : null;

  const selectedForeachRuntime = useMemo(() => {
    if (!selectedNodeState) {
      return null;
    }
    if (selectedNodeState.node_kind === 'foreach') {
      return foreachByNodeId.get(selectedNodeState.node_id) ?? null;
    }
    const parentNodeId = selectedFlowNode?.parent_node_id;
    if (!parentNodeId) {
      return null;
    }
    return foreachByNodeId.get(parentNodeId) ?? null;
  }, [foreachByNodeId, selectedFlowNode?.parent_node_id, selectedNodeState]);

  // Resolve parent flow slug for breadcrumb.
  const parentFlow = flowsQuery.data?.find((flow) => flow.id === run?.flow_id);
  const parentFlowHref = parentFlow ? `/flows/${parentFlow.slug}` : '/flows';

  useEffect(() => {
    useWorkbenchStore.getState().reset();
  }, [runId]);

  useEffect(() => {
    if (!selectedNodeStateId && topLevelStates.length > 0) {
      setSelectedNodeStateId(topLevelStates[0].id);
    }
  }, [selectedNodeStateId, setSelectedNodeStateId, topLevelStates]);

  useEffect(() => {
    if (selectedNodeState && selectedNodeState.loop_iteration_id && !selectedIterationId) {
      setSelectedIterationId(selectedNodeState.loop_iteration_id);
    }
  }, [selectedIterationId, selectedNodeState, setSelectedIterationId]);

  if (runQuery.isLoading) {
    return (
      <div className="border border-border/70 bg-card/70 px-4 py-8 text-sm text-muted-foreground">
        Loading run…
      </div>
    );
  }

  if (runQuery.error || !run) {
    return (
      <div className="border border-rose-400/30 bg-rose-500/10 px-4 py-8 text-sm text-rose-100">
        Failed to load the requested run.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header: breadcrumb + run title + controls */}
      <section className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <nav className="flex items-center gap-2 text-xs text-muted-foreground">
              <Link to="/flows" className="hover:text-accent">Flows</Link>
              <span>/</span>
              <Link to={parentFlowHref} className="hover:text-accent">
                {parentFlow?.title ?? parentFlow?.slug ?? run.flow_id}
              </Link>
              <span>/</span>
              <span className="text-foreground/70">runs</span>
            </nav>
            <p className="mt-2 text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Run workbench</p>
            <h1 className="mt-1 text-4xl font-bold uppercase tracking-[0.1em] text-accent">{run.id}</h1>
            <div className="mt-1 flex flex-wrap gap-2 text-sm text-muted-foreground">
              <span>Status: {run.status}</span>
              <span>Flow: {run.flow_id}</span>
              <span>Version: {run.flow_version_id}</span>
            </div>
          </div>
          <RunControls
            onRefresh={() => runQuery.refetch()}
            runId={run.id}
            status={run.status}
          />
        </div>
      </section>

      {/* Main grid: tree (left) + inspector (right) */}
      <section className="grid gap-6 xl:grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.85fr)]">
        <div className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">Tree</p>
              <h2 className="mt-1 text-lg font-semibold uppercase tracking-[0.15em] text-accent">Flow tree</h2>
            </div>
            <div className="text-sm text-muted-foreground">{flattenedNodes.length} nodes</div>
          </div>
          <NodeTree
            nodes={flowVersion?.nodes ?? []}
            nodeStates={run.node_states}
            onSelectNode={(nodeId) => {
              const stateId = nodeIdToStateId.get(nodeId);
              if (stateId) setSelectedNodeStateId(stateId);
            }}
            selectedNodeId={selectedNodeState?.node_id}
          />
        </div>
        <RunInspectorPane
          activeTab={activeTab}
          flowNode={selectedFlowNode}
          foreachRuntime={selectedForeachRuntime}
          onSelectTab={setActiveTab}
          selectedIterationId={selectedIterationId}
          selectedNodeState={selectedNodeState}
        />
      </section>

      {/* Bottom: console */}
      <WorkbenchConsole run={run} />
    </div>
  );
}
