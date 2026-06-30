import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import { type ReactElement, type ReactNode } from 'react';
import { MemoryRouter, type MemoryRouterProps } from 'react-router';

/**
 * Create a fresh QueryClient for each test with deterministic defaults:
 * - No retries (so error states surface immediately)
 * - No staleTime (so refetches hit MSW predictably)
 * - No refetchInterval (prevents polling unless explicitly enabled)
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
        refetchInterval: false,
      },
      mutations: { retry: false },
    },
  });
}

interface RenderWithRouterOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial route entries for MemoryRouter. Defaults to ['/']. */
  initialEntries?: MemoryRouterProps['initialEntries'];
  /** Initial index for MemoryRouter. */
  initialIndex?: number;
  /** Custom QueryClient if a test needs specific config. */
  queryClient?: QueryClient;
}

/**
 * Render a component inside the same provider stack the app uses:
 * QueryClientProvider + MemoryRouter.
 *
 * Usage:
 *   const { getByText } = renderWithRouter(<FlowsListView />, { initialEntries: ['/flows'] });
 */
export function renderWithRouter(
  ui: ReactElement,
  options: RenderWithRouterOptions = {},
) {
  const {
    initialEntries = ['/'],
    initialIndex = 0,
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

/**
 * Render a component with full route definitions (for testing
 * navigation between routes). Uses MemoryRouter + Routes.
 */
export function renderWithRoutes(
  routes: ReactElement,
  options: Omit<RenderWithRouterOptions, 'wrapper'> = {},
) {
  const {
    initialEntries = ['/'],
    initialIndex = 0,
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(routes, { wrapper: Wrapper, ...renderOptions });
}

export { createTestQueryClient as makeQueryClient };
