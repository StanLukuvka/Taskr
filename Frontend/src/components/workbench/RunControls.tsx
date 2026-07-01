// FLOW-PRODUCED: /agent/projects/taskr/Frontend/.hermes/plans/2026-06-30_m1-visual-cleanup.md
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import {
  isTerminalRun,
  useCancelRun,
  useDeleteRun,
  useRetryRun,
  useTickRun,
} from '@/hooks/use-taskr';
import type { RunStatus } from '@/types/taskr';

interface RunControlsProps {
  onRefresh: () => Promise<unknown>;
  runId: string;
  status: RunStatus;
}

export function RunControls({ onRefresh, runId, status }: RunControlsProps) {
  const navigate = useNavigate();
  const tickMutation = useTickRun();
  const cancelMutation = useCancelRun();
  const retryMutation = useRetryRun();
  const deleteMutation = useDeleteRun();
  const terminal = isTerminalRun({ status });

  return (
    <div className="flex flex-wrap gap-3">
      <Button
        disabled={terminal || tickMutation.isPending}
        onClick={() => {
          void tickMutation.mutateAsync(runId).then(() => onRefresh());
        }}
      >
        {terminal ? 'Run' : tickMutation.isPending ? 'Running…' : 'Running…'}
      </Button>
      <Button
        variant="secondary"
        disabled={terminal || cancelMutation.isPending}
        onClick={() => {
          void cancelMutation.mutateAsync(runId).then(() => onRefresh());
        }}
      >
        {cancelMutation.isPending ? 'Cancelling…' : 'Cancel'}
      </Button>
      <Button
        variant="outline"
        disabled={retryMutation.isPending}
        onClick={() => {
          void retryMutation.mutateAsync(runId).then((run) => {
            navigate(`/runs/${run.id}`);
          });
        }}
      >
        {retryMutation.isPending ? 'Retrying…' : 'Retry'}
      </Button>
      <Button variant="ghost" onClick={() => void onRefresh()}>
        Refresh
      </Button>
      <Button
        variant="destructive"
        disabled={deleteMutation.isPending}
        onClick={() => {
          void deleteMutation.mutateAsync(runId).then(() => {
            navigate('/runs');
          });
        }}
      >
        {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
      </Button>
    </div>
  );
}
