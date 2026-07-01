import type { RunStatus, NodeStateStatus } from '@/types/taskr';

export const runStatusClasses: Record<RunStatus, string> = {
  pending: 'bg-slate-500/15 text-slate-200 ring-slate-400/30',
  running: 'bg-cyan-500/15 text-cyan-200 ring-cyan-400/30',
  paused: 'bg-amber-500/15 text-amber-200 ring-amber-400/30',
  completed: 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/30',
  failed: 'bg-rose-500/15 text-rose-200 ring-rose-400/30',
  cancelled: 'bg-zinc-500/15 text-zinc-200 ring-zinc-400/30',
};

export const nodeStatusClasses: Record<NodeStateStatus, string> = {
  pending: 'bg-slate-500/15 text-slate-200 ring-slate-400/30',
  ready: 'bg-indigo-500/15 text-indigo-200 ring-indigo-400/30',
  dispatching: 'bg-sky-500/15 text-sky-200 ring-sky-400/30',
  running: 'bg-orange-500/15 text-orange-200 ring-orange-400/30 border-orange-400/30',
  completed: 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/30 border-emerald-400/30',
  failed: 'bg-rose-500/15 text-rose-200 ring-rose-400/30 border-rose-400/30',
  cancelled: 'bg-zinc-500/15 text-zinc-200 ring-zinc-400/30',
};

export const nodeCardBorderClasses: Record<NodeStateStatus, string> = {
  pending: 'border-slate-400/20',
  ready: 'border-indigo-400/20',
  dispatching: 'border-sky-400/20',
  running: 'border-orange-400/50 bg-orange-500/5',
  completed: 'border-emerald-400/50 bg-emerald-500/5',
  failed: 'border-rose-400/50 bg-rose-500/5',
  cancelled: 'border-zinc-400/20',
};
