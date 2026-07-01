import { describe, expect, it } from 'vitest';
import { flows, activeFlow } from '@/tests/fixtures/flows';
import { baseRun } from '@/tests/fixtures/runs';
import type { CreateRunRequest, FlowSummary, Run } from '@/types/taskr';

/**
 * Direct-fetch verification of MSW handlers.
 *
 * These tests bypass React entirely and call fetch() directly against
 * the endpoints that the MSW handlers in src/tests/mocks/handlers.ts
 * intercept. They prove that:
 *  1. The MSW server is listening (setup.ts beforeAll).
 *  2. The handlers return realistic mock payloads with correct shapes.
 *  3. The server resets between tests (setup.ts afterEach).
 *
 * The real backend API uses /flows, /flows/:slug, and POST /runs (not
 * /api/flows/:id/runs) — these tests match that contract.
 */
describe('MSW handlers — direct fetch', () => {
  it('GET /flows returns FlowSummary[]', async () => {
    const res = await fetch('/flows');
    expect(res.ok).toBe(true);
    const data = (await res.json()) as FlowSummary[];
    expect(data).toHaveLength(flows.length);
    expect(data[0].slug).toBe(activeFlow.slug);
    expect(data[0].title).toBe(activeFlow.title);
    expect(data[0].active_flow_version_id).toBe(activeFlow.active_flow_version_id);
  });

  it('GET /flows/:slug returns the matching FlowSummary', async () => {
    const res = await fetch(`/flows/${activeFlow.slug}`);
    expect(res.ok).toBe(true);
    const data = (await res.json()) as FlowSummary;
    expect(data.id).toBe(activeFlow.id);
    expect(data.slug).toBe(activeFlow.slug);
  });

  it('GET /flows/:slug returns 404 for an unknown slug', async () => {
    const res = await fetch('/flows/nonexistent');
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.detail).toContain('not found');
  });

  it('POST /runs creates and returns a Run with pending status', async () => {
    const payload: CreateRunRequest = {
      flow_slug: activeFlow.slug,
      context: { retailer: 'woolworths', category: 'soda' },
    };
    const res = await fetch('/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(res.ok).toBe(true);
    const data = (await res.json()) as Run;
    expect(data.status).toBe('pending');
    expect(data.flow_id).toBe(activeFlow.id);
    expect(data.flow_version_id).toBe(activeFlow.active_flow_version_id);
    expect(data.id).not.toBe(baseRun.id);
  });

  it('server resets state between tests — base run is unaffected by prior POST', async () => {
    // If resetMockStore() in afterEach works, the createdRuns map is empty
    // and a GET /runs returns only the seed makeRunItem (baseRun).
    const res = await fetch('/runs');
    expect(res.ok).toBe(true);
    const data = await res.json();
    // The first item is always the seed makeRunItem; no leftover created runs.
    expect(data[0].id).toBe(baseRun.id);
  });
});
