import type { FlowNode, FlowVersion } from '@/types/taskr';

export const flowNodes: FlowNode[] = [
  {
    id: 'node-api-1',
    kind: 'api',
    ord: 0,
    title: 'Fetch prices',
    parent_node_id: null,
    binding_id: 'bind-api-1',
    input_mapping: { sku: '$.context.sku' },
    output_mapping: { price: '$.result.price' },
    items_path: null,
    item_key_path: null,
    failure_policy: 'stop',
    policy_refs: null,
    children: [],
  },
  {
    id: 'node-foreach-1',
    kind: 'foreach',
    ord: 1,
    title: 'Loop over retailers',
    parent_node_id: null,
    binding_id: null,
    input_mapping: null,
    output_mapping: null,
    items_path: '$.context.retailers',
    item_key_path: null,
    failure_policy: 'continue',
    policy_refs: null,
    children: [
      {
        id: 'node-hermes-1',
        kind: 'hermes',
        ord: 0,
        title: 'Review item',
        parent_node_id: 'node-foreach-1',
        binding_id: 'bind-hermes-1',
        input_mapping: { item: '$.item' },
        output_mapping: { verdict: '$.output.verdict' },
        items_path: null,
        item_key_path: null,
        failure_policy: 'stop',
        policy_refs: null,
        children: [],
      },
    ],
  },
];

export const flowVersion: FlowVersion = {
  id: 'fv-1',
  flow_id: 'flow-1',
  version: 3,
  status: 'active',
  nodes: flowNodes,
};
