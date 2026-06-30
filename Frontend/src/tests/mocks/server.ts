import { setupServer } from 'msw/node';
import { handlers, resetMockStore } from './handlers';

/**
 * MSW server for integration tests. Started once in setup.ts.
 * Tests can override handlers via `server.use(...)` or reset via
 * `server.resetHandlers(...)` then re-apply.
 */
export const server = setupServer(...handlers);

export { resetMockStore, handlers };
