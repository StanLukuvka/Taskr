import { describe, expect, it } from 'vitest';
import { formatCurrencyCents, formatTimestamp } from '@/lib/formatters';
import { formatJson } from '@/lib/utils';

describe('formatter helpers', () => {
  it('formats cents as dollars', () => {
    expect(formatCurrencyCents(250)).toBe('$2.50');
  });

  it('formats missing timestamps as em dash', () => {
    expect(formatTimestamp(null)).toBe('—');
  });

  it('formats JSON values consistently', () => {
    expect(formatJson({ ok: true })).toContain('"ok": true');
  });
});
