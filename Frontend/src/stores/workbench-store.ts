import { create } from 'zustand';
import type { InspectorTab } from '@/types/taskr';

interface WorkbenchState {
  activeTab: InspectorTab;
  selectedIterationId: string | null;
  selectedNodeStateId: string | null;
  setActiveTab: (tab: InspectorTab) => void;
  setSelectedIterationId: (iterationId: string | null) => void;
  setSelectedNodeStateId: (nodeStateId: string | null) => void;
  reset: () => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  activeTab: 'overview',
  selectedIterationId: null,
  selectedNodeStateId: null,
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedIterationId: (selectedIterationId) => set({ selectedIterationId }),
  setSelectedNodeStateId: (selectedNodeStateId) => set({ selectedNodeStateId }),
  reset: () =>
    set({
      activeTab: 'overview',
      selectedIterationId: null,
      selectedNodeStateId: null,
    }),
}));
