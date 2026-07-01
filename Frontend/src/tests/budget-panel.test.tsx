import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BudgetPanel } from '@/components/workbench/BudgetPanel';

describe('BudgetPanel — real spend props (t_3e8e8274)', () => {
  it('shows spent and — for cap when no cap provided', () => {
    render(<BudgetPanel totalCostCents={150} />);
    // formatCurrencyCents(150) = $1.50
    expect(screen.getByText('$1.50')).toBeDefined();
    expect(screen.getByText('—')).toBeDefined();
  });

  it('shows spent, cap, remaining, and progress when cap is set', () => {
    render(<BudgetPanel totalCostCents={30} budgetCents={100} label="Demo" />);
    expect(screen.getByText('Demo')).toBeDefined();
    expect(screen.getByText('$0.30')).toBeDefined(); // spent
    expect(screen.getByText('$1.00')).toBeDefined(); // cap
    expect(screen.getByText('$0.70')).toBeDefined(); // remaining
  });

  it('shows exhausted status and rose bar when spent >= cap', () => {
    const { container } = render(
      <BudgetPanel totalCostCents={150} budgetCents={100} />,
    );
    expect(screen.getByText('Exhausted')).toBeDefined();
    const bar = container.querySelector('.h-full');
    expect(bar?.className).toContain('bg-rose-500/80');
  });

  it('shows near-threshold status and amber bar at threshold', () => {
    const { container } = render(
      <BudgetPanel totalCostCents={85} budgetCents={100} threshold={0.8} />,
    );
    expect(screen.getByText('Near threshold')).toBeDefined();
    const bar = container.querySelector('.h-full');
    expect(bar?.className).toContain('bg-amber-500/80');
  });

  it('defaults to 0 spent when totalCostCents is 0 (no NaN)', () => {
    render(<BudgetPanel totalCostCents={0} budgetCents={100} />);
    expect(screen.getByText('$0.00')).toBeDefined();
    expect(screen.getByText('Under budget')).toBeDefined();
  });
});
