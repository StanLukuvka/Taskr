import { describe, expect, it } from 'vitest';
import { act, screen, waitFor, fireEvent } from '@testing-library/react';
import { Link, Route, Routes } from 'react-router';
import { renderWithProviders } from './renderWithProviders';

// --- Minimal route components for testing navigation ---

function Home() {
  return <div data-testid="home">Home Page</div>;
}

function Flows() {
  return (
    <div>
      <div data-testid="flows">Flows Page</div>
      <Link to="/runs" data-testid="goto-runs">
        Go to Runs
      </Link>
    </div>
  );
}

function Runs() {
  return <div data-testid="runs">Runs Page</div>;
}

const testRoutes = (
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/flows" element={<Flows />} />
    <Route path="/runs" element={<Runs />} />
  </Routes>
);

// --- Tests ---

describe('renderWithProviders', () => {
  it('renders a component at the specified initial route', () => {
    const { router } = renderWithProviders(testRoutes, {
      initialEntries: ['/flows'],
    });

    expect(screen.getByTestId('flows')).toBeInTheDocument();
    expect(router.location.pathname).toBe('/flows');
  });

  it('defaults to "/" when no initialEntries are provided', () => {
    const { router } = renderWithProviders(testRoutes);

    expect(screen.getByTestId('home')).toBeInTheDocument();
    expect(router.location.pathname).toBe('/');
  });

  it('reflects navigation state after clicking a Link', async () => {
    const { router } = renderWithProviders(testRoutes, {
      initialEntries: ['/flows'],
    });

    expect(router.location.pathname).toBe('/flows');

    fireEvent.click(screen.getByTestId('goto-runs'));

    await waitFor(() => {
      expect(router.location.pathname).toBe('/runs');
    });
    expect(screen.getByTestId('runs')).toBeInTheDocument();
  });

  it('supports programmatic navigation via router.navigate', async () => {
    const { router } = renderWithProviders(testRoutes, {
      initialEntries: ['/'],
    });

    expect(router.location.pathname).toBe('/');

    act(() => {
      router.navigate('/flows');
    });

    expect(router.location.pathname).toBe('/flows');
    expect(screen.getByTestId('flows')).toBeInTheDocument();
  });

  it('captures search params and hash in router.location', () => {
    const { router } = renderWithProviders(testRoutes, {
      initialEntries: ['/flows?sort=desc#section-2'],
    });

    expect(router.location.pathname).toBe('/flows');
    expect(router.location.search).toBe('?sort=desc');
    expect(router.location.hash).toBe('#section-2');
  });
});
