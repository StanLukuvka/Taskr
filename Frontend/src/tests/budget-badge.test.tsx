import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BudgetBadge } from '@/components/runs/BudgetBadge';
import type { RunListItem } from '@/types/taskr';

function makeRun(overrides: Partial<RunListItem> = {}): RunListItem {
  return {
    id: 'run-test',
    status: 'running',
    flow_id: 'flow-1',
    flow_version_id: 'fv-1',
    total_cost_cents: 0,
    created_at: '2026-06-30T10:00:00Z',
    started_at: '2026-06-30T10:00:05Z',
    finished_at: null,
    ...overrides,
  };
}

const KEYS = ['taskr.budget.cents', 'taskr.budget.threshold', 'taskr.budget.label'];

afterEach(() => {
  for (const k of KEYS) localStorage.removeItem(k);
});

describe('BudgetBadge — real spend from total_cost_cents (t_3e8e8274)', () => {
  it('shows formatted spend when no localStorage cap is set', () => {
    render(<BudgetBadge run={makeRun({ total_cost_cents: 150 })} />);
    // formatCurrencyCents(150) = $1.50
    expect(screen.getByText('$1.50')).toBeDefined();
  });

  it('defaults to $0.00 when total_cost_cents is null/undefined', () => {
    render(<BudgetBadge run={makeRun({ total_cost_cents: 0 })} />);
    expect(screen.getByText('$0.00')).toBeDefined();
  });

  it('shows remaining/cap and progress bar when localStorage cap is set', () => {
    localStorage.setItem('taskr.budget.cents', '100');
    localStorage.setItem('taskr.budget.label', 'Demo budget');
    const { container } = render(
      <BudgetBadge run={makeRun({ total_cost_cents: 30 })} />,
    );
    expect(screen.getByText('Demo budget')).toBeDefined();
    // remaining = 100 - 30 = 70 => $0.70 / $1.00
    expect(screen.getByText('$0.70 / $1.00')).toBeDefined();
    const bar = container.querySelector('.h-full');
    expect(bar).toBeDefined();
  });

  it('shows rose styling when budget exhausted', () => {
    localStorage.setItem('taskr.budget.cents', '100');
    const { container } = render(
      <BudgetBadge run={makeRun({ total_cost_cents: 150 })} />,
    );
    const remainingText = screen.getByText('$0.00 / $1.00');
    expect(remainingText.className).toContain('text-rose-300');
    const bar = container.querySelector('.h-full');
    expect(bar?.className).toContain('bg-rose-500/80');
  });

  it('falls back to Budget label when no label in localStorage', () => {
    localStorage.setItem('taskr.budget.cents', '200');
    render(<BudgetBadge run={makeRun({ total_cost_cents: 0 })} />);
    expect(screen.getByText('Budget')).toBeDefined();
  });

  it('uses amber bar color near threshold', () => {
    localStorage.setItem('taskr.budget.cents', '100');
    localStorage.setItem('taskr.budget.threshold', '0.8');
    const { container } = render(
      <BudgetBadge run={makeRun({ total_cost_cents: 85 })} />,
    );
    const bar = container.querySelector('.h-full');
    expect(bar?.className).toContain('bg-amber-500/80');
  });
});
