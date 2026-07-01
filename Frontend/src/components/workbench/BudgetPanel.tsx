import { formatCurrencyCents } from '@/lib/formatters';

interface BudgetPanelProps {
  totalCostCents: number;
  budgetCents?: number | null;
  threshold?: number;
  label?: string;
}

/**
 * Workbench budget panel. Always shows actual spend; when a cap is provided,
 * also shows cap, remaining, and a progress bar with status.
 */
export function BudgetPanel({
  totalCostCents,
  budgetCents,
  threshold = 0.8,
  label = 'Budget',
}: BudgetPanelProps) {
  const spent = totalCostCents ?? 0;
  const cap = budgetCents != null && budgetCents > 0 ? budgetCents : null;

  if (cap == null) {
    return (
      <div className="border border-border/70 bg-black/10 p-4">
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
          {label}
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <BudgetStat label="Spent" value={formatCurrencyCents(spent)} />
          <BudgetStat label="Cap" value="—" />
        </div>
      </div>
    );
  }

  const remaining = Math.max(0, cap - spent);
  const exhausted = remaining <= 0;
  const pct = cap > 0 ? Math.min(100, (spent / cap) * 100) : 0;
  const nearThreshold = pct >= threshold * 100;
  const barColor = exhausted
    ? 'bg-rose-500/80'
    : nearThreshold
      ? 'bg-amber-500/80'
      : 'bg-accent/80';
  const status = exhausted
    ? 'Exhausted'
    : nearThreshold
      ? 'Near threshold'
      : 'Under budget';

  return (
    <div className="border border-border/70 bg-black/10 p-4">
      <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <BudgetStat label="Spent" value={formatCurrencyCents(spent)} />
        <BudgetStat label="Cap" value={formatCurrencyCents(cap)} />
        <BudgetStat label="Remaining" value={formatCurrencyCents(remaining)} />
      </div>
      <div className="mt-3">
        <div className="h-2 w-full bg-black/30">
          <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{pct.toFixed(0)}%</span>
          <span className={exhausted ? 'text-rose-300' : ''}>{status}</span>
        </div>
      </div>
    </div>
  );
}

interface BudgetStatProps {
  label: string;
  value: string;
}

function BudgetStat({ label, value }: BudgetStatProps) {
  return (
    <div className="border border-border/70 bg-black/10 p-3">
      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm text-foreground/90">{value}</div>
    </div>
  );
}
