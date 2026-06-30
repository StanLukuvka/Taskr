import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from '@/tests/mocks/server';
import { resetMockStore } from '@/tests/mocks/handlers';

// Start MSW server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset handlers and mock store between tests so each test is isolated
afterEach(() => {
  server.resetHandlers();
  resetMockStore();
});

// Clean up after all tests
afterAll(() => server.close());
