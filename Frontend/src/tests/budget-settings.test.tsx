import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { BudgetSettingsPage } from '@/pages/BudgetSettingsPage';
import { renderWithRouter } from '@/tests/render-with-router';
import { useBudgetSettings } from '@/hooks/use-budget-settings';

const CENTS_KEY = 'taskr.budget.cents';
const THRESHOLD_KEY = 'taskr.budget.threshold';
const LABEL_KEY = 'taskr.budget.label';

function clearStorage() {
  localStorage.removeItem(CENTS_KEY);
  localStorage.removeItem(THRESHOLD_KEY);
  localStorage.removeItem(LABEL_KEY);
}

beforeEach(clearStorage);
afterEach(clearStorage);

// ---------------------------------------------------------------------------
// Hook: useBudgetSettings — localStorage save/load/validation
// ---------------------------------------------------------------------------

describe('useBudgetSettings — localStorage persistence', () => {
  it('returns defaults when localStorage is empty', () => {
    const { result } = renderHook(() => useBudgetSettings());
    expect(result.current.budgetCents).toBeNull();
    expect(result.current.threshold).toBe(0.8);
    expect(result.current.label).toBe('Budget');
  });

  it('loads values from localStorage on init', () => {
    localStorage.setItem(CENTS_KEY, '5000');
    localStorage.setItem(THRESHOLD_KEY, '0.9');
    localStorage.setItem(LABEL_KEY, 'Monthly budget');
    const { result } = renderHook(() => useBudgetSettings());
    expect(result.current.budgetCents).toBe(5000);
    expect(result.current.threshold).toBe(0.9);
    expect(result.current.label).toBe('Monthly budget');
  });

  it('persists budgetCents to localStorage via setBudgetCents', () => {
    const { result } = renderHook(() => useBudgetSettings());
    act(() => result.current.setBudgetCents(3000));
    expect(result.current.budgetCents).toBe(3000);
    expect(localStorage.getItem(CENTS_KEY)).toBe('3000');
  });

  it('clearing the cap removes cents, threshold, and label from localStorage', () => {
    localStorage.setItem(CENTS_KEY, '5000');
    localStorage.setItem(THRESHOLD_KEY, '0.9');
    localStorage.setItem(LABEL_KEY, 'My budget');
    const { result } = renderHook(() => useBudgetSettings());
    expect(result.current.budgetCents).toBe(5000);

    act(() => result.current.setBudgetCents(null));

    expect(result.current.budgetCents).toBeNull();
    expect(result.current.threshold).toBe(0.8);
    expect(result.current.label).toBe('Budget');
    expect(localStorage.getItem(CENTS_KEY)).toBeNull();
    expect(localStorage.getItem(THRESHOLD_KEY)).toBeNull();
    expect(localStorage.getItem(LABEL_KEY)).toBeNull();
  });

  it('clamps threshold to 0..1', () => {
    const { result } = renderHook(() => useBudgetSettings());
    act(() => result.current.setThreshold(1.5));
    expect(result.current.threshold).toBe(1);
    expect(localStorage.getItem(THRESHOLD_KEY)).toBe('1');

    act(() => result.current.setThreshold(-0.2));
    expect(result.current.threshold).toBe(0);
    expect(localStorage.getItem(THRESHOLD_KEY)).toBe('0');

    act(() => result.current.setThreshold(0.65));
    expect(result.current.threshold).toBe(0.65);
  });

  it('persists label via setLabel', () => {
    const { result } = renderHook(() => useBudgetSettings());
    act(() => result.current.setLabel('Quarterly cap'));
    expect(result.current.label).toBe('Quarterly cap');
    expect(localStorage.getItem(LABEL_KEY)).toBe('Quarterly cap');
  });

  it('resets malformed localStorage values to defaults', () => {
    localStorage.setItem(CENTS_KEY, 'not-a-number');
    localStorage.setItem(THRESHOLD_KEY, 'NaN');
    const { result } = renderHook(() => useBudgetSettings());
    expect(result.current.budgetCents).toBeNull();
    expect(result.current.threshold).toBe(0.8);
  });

  it('resets negative budget values to null', () => {
    localStorage.setItem(CENTS_KEY, '-100');
    const { result } = renderHook(() => useBudgetSettings());
    expect(result.current.budgetCents).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Page: BudgetSettingsPage — save/load/clear interactions
// ---------------------------------------------------------------------------

describe('BudgetSettingsPage — save and clear interactions', () => {
  it('renders with default values when no localStorage', () => {
    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });
    // Number inputs return null when empty
    expect(screen.getByLabelText(/monthly cap/i)).toHaveValue(null);
    expect(screen.getByLabelText(/alert threshold/i)).toHaveValue(80);
    expect(screen.getByLabelText(/label/i)).toHaveValue('Budget');
  });

  it('saves cap, threshold, and label to localStorage on Save', async () => {
    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });

    fireEvent.change(screen.getByLabelText(/monthly cap/i), { target: { value: '50.00' } });
    fireEvent.change(screen.getByLabelText(/alert threshold/i), { target: { value: '75' } });
    fireEvent.change(screen.getByLabelText(/label/i), { target: { value: 'Monthly budget' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    // $50.00 = 5000 cents
    expect(localStorage.getItem(CENTS_KEY)).toBe('5000');
    expect(localStorage.getItem(THRESHOLD_KEY)).toBe('0.75');
    expect(localStorage.getItem(LABEL_KEY)).toBe('Monthly budget');

    // Saved indicator appears
    await waitFor(() => {
      expect(screen.getByText('Saved')).toBeInTheDocument();
    });
  });

  it('clears all budget keys from localStorage on Clear cap', () => {
    localStorage.setItem(CENTS_KEY, '5000');
    localStorage.setItem(THRESHOLD_KEY, '0.75');
    localStorage.setItem(LABEL_KEY, 'Monthly budget');

    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });
    fireEvent.click(screen.getByRole('button', { name: /clear cap/i }));

    expect(localStorage.getItem(CENTS_KEY)).toBeNull();
    expect(localStorage.getItem(THRESHOLD_KEY)).toBeNull();
    expect(localStorage.getItem(LABEL_KEY)).toBeNull();
  });

  it('shows current spend from runs list (MSW)', async () => {
    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });

    // MSW returns one run with total_cost_cents: 0 → $0.00
    await waitFor(() => {
      expect(screen.getByText(/\$0\.00/)).toBeInTheDocument();
    });
  });

  it('shows live progress bar when a cap is entered', async () => {
    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });

    // Enter a cap so the preview bar appears
    fireEvent.change(screen.getByLabelText(/monthly cap/i), { target: { value: '10.00' } });

    // The progress bar track exists (bg-black/40 container)
    const bar = document.querySelector('.bg-black\\/40');
    expect(bar).not.toBeNull();
  });

  it('shows Under budget status when spend is below cap', async () => {
    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });
    fireEvent.change(screen.getByLabelText(/monthly cap/i), { target: { value: '10.00' } });

    await waitFor(() => {
      expect(screen.getByText('Under budget')).toBeInTheDocument();
    });
  });

  it('restores saved values from localStorage on remount', () => {
    localStorage.setItem(CENTS_KEY, '5000');
    localStorage.setItem(THRESHOLD_KEY, '0.9');
    localStorage.setItem(LABEL_KEY, 'Quarterly cap');

    renderWithRouter(<BudgetSettingsPage />, { initialEntries: ['/budget'] });

    // 5000 cents = $50.00, displayed as number 50 in input
    expect(screen.getByLabelText(/monthly cap/i)).toHaveValue(50);
    expect(screen.getByLabelText(/alert threshold/i)).toHaveValue(90);
    expect(screen.getByLabelText(/label/i)).toHaveValue('Quarterly cap');
  });
});
