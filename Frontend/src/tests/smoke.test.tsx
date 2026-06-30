import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { FlowsListView } from '@/components/flows/FlowsListView';
import { renderWithRouter } from '@/tests/render-with-router';
import { flows } from '@/tests/fixtures/flows';

/**
 * Smoke test: validates the entire integration test harness.
 * If this passes, the following are all working:
 * - MSW server lifecycle (setup.ts: beforeAll/afterEach/afterAll)
 * - Mock handlers (GET /flows intercepted and returning fixture data)
 * - renderWithRouter helper (QueryClientProvider + MemoryRouter)
 * - Fixtures (flows shape matches FlowSummary[])
 * - apiRequest client (fetch reaches MSW in jsdom)
 */
describe('integration test harness smoke test', () => {
  it('renders FlowsListView with mocked /flows data', async () => {
    renderWithRouter(<FlowsListView />, { initialEntries: ['/flows'] });

    // The loading state should appear first
    expect(screen.getByText(/Loading flows/i)).toBeInTheDocument();

    // Wait for MSW to respond and the component to re-render
    await waitFor(() => {
      expect(screen.getByText(flows[0].title)).toBeInTheDocument();
    });

    // Both flows from the fixture should be rendered
    expect(screen.getByText(flows[0].title)).toBeInTheDocument();
    expect(screen.getByText(flows[1].title)).toBeInTheDocument();

    // The active flow should link to /flows/{slug}
    expect(screen.getByRole('link', { name: flows[0].title })).toHaveAttribute(
      'href',
      `/flows/${flows[0].slug}`,
    );

    // The inactive flow (no active_flow_version_id) should NOT be a link
    // and should show the "(no active version)" indicator
    expect(screen.getByText(/no active version/i)).toBeInTheDocument();

    // Run flow button should be disabled for inactive flow, enabled for active
    const runButtons = screen.getAllByRole('button', { name: /Run flow/i });
    expect(runButtons).toHaveLength(2);
    expect(runButtons[0]).not.toBeDisabled();
    expect(runButtons[1]).toBeDisabled();
  });
});
