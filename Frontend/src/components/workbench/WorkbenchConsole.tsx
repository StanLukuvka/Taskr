// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m2-flows-workbench.md
import { useMemo } from 'react';
import { nodeStatusClasses } from '@/lib/status-styles';
import type { NodeStateStatus, Run } from '@/types/taskr';

interface ConsoleEvent {
  id: string;
  timestamp: string | null;
  nodeTitle: string;
  nodeId: string;
  fromStatus: NodeStateStatus | null;
  toStatus: NodeStateStatus;
  errorMessage: string | null;
}

interface WorkbenchConsoleProps {
  run: Run;
  previousRun?: Run | null;
}

/**
 * Derive a chronological event log from the run's node_states.
 *
 * When `previousRun` is supplied, only states that are new or whose status
 * changed between ticks produce an event (the diff path). When it is absent
 * the full lifecycle is reconstructed from each state's created/started/
 * finished timestamp fields.
 */
function deriveEvents(run: Run, previousRun?: Run | null): ConsoleEvent[] {
  if (previousRun) {
    const prevById = new Map(previousRun.node_states.map((s) => [s.id, s] as const));
    const events: ConsoleEvent[] = [];

    for (const state of run.node_states) {
      const prev = prevById.get(state.id);
      const title = state.node_title ?? state.node_id;

      if (!prev) {
        events.push({
          id: `${state.id}:new`,
          timestamp: state.updated_at ?? state.created_at,
          nodeTitle: title,
          nodeId: state.node_id,
          fromStatus: null,
          toStatus: state.status,
          errorMessage: state.error_message,
        });
      } else if (prev.status !== state.status) {
        events.push({
          id: `${state.id}:${prev.status}->${state.status}`,
          timestamp: state.updated_at,
          nodeTitle: title,
          nodeId: state.node_id,
          fromStatus: prev.status,
          toStatus: state.status,
          errorMessage: state.error_message,
        });
      }
    }

    return events.sort((a, b) => (a.timestamp ?? '').localeCompare(b.timestamp ?? ''));
  }

  // No previous tick — reconstruct lifecycle from timestamp fields.
  const events: ConsoleEvent[] = [];
  for (const state of run.node_states) {
    const title = state.node_title ?? state.node_id;

    if (state.created_at) {
      events.push({
        id: `${state.id}:created`,
        timestamp: state.created_at,
        nodeTitle: title,
        nodeId: state.node_id,
        fromStatus: null,
        toStatus: 'pending',
        errorMessage: null,
      });
    }
    if (state.started_at) {
      events.push({
        id: `${state.id}:started`,
        timestamp: state.started_at,
        nodeTitle: title,
        nodeId: state.node_id,
        fromStatus: 'pending',
        toStatus: 'running',
        errorMessage: null,
      });
    }
    if (state.finished_at) {
      events.push({
        id: `${state.id}:finished`,
        timestamp: state.finished_at,
        nodeTitle: title,
        nodeId: state.node_id,
        fromStatus: 'running',
        toStatus: state.status,
        errorMessage: state.status === 'failed' ? state.error_message : null,
      });
    }
  }

  return events.sort((a, b) => (a.timestamp ?? '').localeCompare(b.timestamp ?? ''));
}

function formatTime(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleTimeString(undefined, { hour12: false });
}

export function WorkbenchConsole({ run, previousRun }: WorkbenchConsoleProps) {
  const events = useMemo(() => deriveEvents(run, previousRun), [run, previousRun]);

  return (
    <section className="border border-border/70 bg-card/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.18)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-accent">Console</h2>
        <span className="font-mono text-xs text-muted-foreground">{events.length} events</span>
      </div>

      {events.length === 0 ? (
        <div className="border border-dashed border-border/50 bg-[#031414] px-3 py-6 text-center font-mono text-xs text-muted-foreground">
          No events yet. Messages will appear as the run progresses.
        </div>
      ) : (
        <div className="max-h-80 overflow-y-auto border border-border/50 bg-[#031414]">
          <table className="w-full border-collapse text-left font-mono text-xs">
            <thead className="sticky top-0 bg-[#031414] text-muted-foreground">
              <tr className="border-b border-border/50">
                <th className="px-3 py-2 font-normal uppercase tracking-wider">Time</th>
                <th className="px-3 py-2 font-normal uppercase tracking-wider">Node</th>
                <th className="px-3 py-2 font-normal uppercase tracking-wider">Transition</th>
                <th className="px-3 py-2 font-normal uppercase tracking-wider">Error</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className="border-b border-border/30 hover:bg-white/5">
                  <td className="whitespace-nowrap px-3 py-1.5 text-muted-foreground">
                    {formatTime(event.timestamp)}
                  </td>
                  <td className="px-3 py-1.5 text-foreground/85">{event.nodeTitle}</td>
                  <td className="whitespace-nowrap px-3 py-1.5">
                    <span className="text-muted-foreground">{event.fromStatus ?? '\u2205'}</span>
                    <span className="mx-1 text-accent">{'\u2192'}</span>
                    <span className={`inline-flex px-1.5 py-0.5 ring-1 ${nodeStatusClasses[event.toStatus]}`}>
                      {event.toStatus}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-rose-200/90">{event.errorMessage ?? '\u2014'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
