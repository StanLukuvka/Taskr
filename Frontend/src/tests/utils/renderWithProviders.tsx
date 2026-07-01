import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import { type ReactElement, type ReactNode } from 'react';
import {
  MemoryRouter,
  useLocation,
  useNavigate,
  type Location,
  type MemoryRouterProps,
  type NavigateFunction,
} from 'react-router';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { createTestQueryClient } from '@/tests/render-with-router';

// Re-export for convenience so tests can import everything from one place.
export { createTestQueryClient } from '@/tests/render-with-router';

/**
 * Router helpers exposed by renderWithProviders.
 * The object is mutable and updated on every navigation, so
 * `result.router.location` always reflects the current route.
 */
export interface RouterHelpers {
  /** Current location — reflects the latest navigation. */
  location: Location;
  /** Programmatic navigate function from react-router. */
  navigate: NavigateFunction;
}

export interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial route entries for MemoryRouter. Defaults to ['/']. */
  initialEntries?: MemoryRouterProps['initialEntries'];
  /** Initial index for MemoryRouter. Defaults to 0. */
  initialIndex?: number;
  /** Custom QueryClient if a test needs specific config. */
  queryClient?: QueryClient;
  /** Wrap with ErrorBoundary to match production. Defaults to false so errors surface in tests. */
  withErrorBoundary?: boolean;
}

export interface RenderWithProvidersResult extends RenderResult {
  /** Router helpers — location and navigate, always reflecting current navigation state. */
  router: RouterHelpers;
}

/**
 * Render a component inside the same provider stack the app uses:
 * QueryClientProvider + MemoryRouter (optionally ErrorBoundary).
 *
 * The returned `router` object is mutable and updated on every render,
 * so `result.router.location.pathname` always reflects the current route
 * — even after programmatic navigation or link clicks.
 *
 * Usage:
 *   const { router, getByText } = renderWithProviders(
 *     <FlowsListView />,
 *     { initialEntries: ['/flows'] },
 *   );
 *   expect(router.location.pathname).toBe('/flows');
 *
 *   // Programmatic navigation
 *   router.navigate('/runs');
 *   await waitFor(() => expect(router.location.pathname).toBe('/runs'));
 */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
): RenderWithProvidersResult {
  const {
    initialEntries = ['/'],
    initialIndex = 0,
    queryClient = createTestQueryClient(),
    withErrorBoundary = false,
    ...renderOptions
  } = options;

  // Mutable object populated by RouterSpy on every render.
  // Returned as `router` so tests always see current navigation state.
  const router = {} as RouterHelpers;

  /** Invisible component that captures router state into the mutable `router` object. */
  function RouterSpy() {
    router.location = useLocation();
    router.navigate = useNavigate();
    return null;
  }

  function Wrapper({ children }: { children: ReactNode }) {
    const content = (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
          <RouterSpy />
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );

    return withErrorBoundary ? <ErrorBoundary>{content}</ErrorBoundary> : content;
  }

  const result = render(ui, { wrapper: Wrapper, ...renderOptions });

  return { ...result, router };
}
