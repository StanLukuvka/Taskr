import { formatCurrencyCents } from '@/lib/formatters';
import type { RunListItem } from '@/types/taskr';
import { useBudgetSettings } from '@/hooks/use-budget-settings';

interface BudgetBadgeProps {
  run: RunListItem;
}

/**
 * Displays actual spend for a run. When a localStorage budget cap is set,
 * also shows remaining/cap and a progress bar.
 */
export function BudgetBadge({ run }: BudgetBadgeProps) {
  const { budgetCents, threshold, label } = useBudgetSettings();
  const spent = run.total_cost_cents ?? 0;

  if (budgetCents == null || budgetCents <= 0) {
    return (
      <span className="font-mono text-xs text-foreground/80">
        {formatCurrencyCents(spent)}
      </span>
    );
  }

  const remaining = Math.max(0, budgetCents - spent);
  const exhausted = remaining <= 0;
  const pct = budgetCents > 0 ? Math.min(100, (spent / budgetCents) * 100) : 0;
  const nearThreshold = pct >= threshold * 100;
  const barColor = exhausted
    ? 'bg-rose-500/80'
    : nearThreshold
      ? 'bg-amber-500/80'
      : 'bg-accent/80';

  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-foreground">{label}</div>
      <div className="h-1.5 w-full bg-black/30">
        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <div
        className={`font-mono text-xs ${exhausted ? 'text-rose-300' : 'text-foreground/80'}`}
      >
        {formatCurrencyCents(remaining)} / {formatCurrencyCents(budgetCents)}
      </div>
    </div>
  );
}
