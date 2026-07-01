import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { FlowsListView } from '@/components/flows/FlowsListView';
import { renderWithRouter } from '@/tests/render-with-router';

/**
 * Integration test for the /flows route.
 *
 * This file mounts the route component (FlowsListView) using the shared
 * rendering harness (renderWithRouter) which wires QueryClientProvider +
 * MemoryRouter. The API client is mocked via MSW — the default handlers
 * in src/tests/mocks/handlers.ts intercept GET /flows and return fixture
 * data, so no per-test API mock is required for the harness to render.
 *
 * Sibling tasks extend this file with assertions that verify specific
 * flow names, slugs, and link clickability against the list_flows.sh
 * data contract.
 */
describe('/flows route integration', () => {
  it('renders without errors using the default harness and MSW handlers', async () => {
    // Mount the /flows route component at the /flows path.
    // No custom API mock is provided — the default MSW handler for
    // GET /flows (from handlers.ts) supplies the fixture data.
    renderWithRouter(<FlowsListView />, { initialEntries: ['/flows'] });

    // The component shows a loading state before the query resolves.
    expect(screen.getByText(/Loading flows/i)).toBeInTheDocument();

    // Wait for the MSW-intercepted response to arrive and the component
    // to render the flows table. If the harness, MSW, or component is
    // broken this will time out and fail.
    await waitFor(() => {
      expect(screen.queryByText(/Loading flows/i)).not.toBeInTheDocument();
    });

    // The table header should be rendered, confirming the component
    // mounted and rendered its main view without throwing.
    expect(screen.getByRole('columnheader', { name: /Slug/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Title/i })).toBeInTheDocument();
  });
});
