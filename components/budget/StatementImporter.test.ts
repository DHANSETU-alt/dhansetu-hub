import { describe, expect, it } from 'vitest';
import { parseStatement } from './StatementImporter';

describe('parseStatement', () => {
  it('normalizes CSV debit rows locally', () => {
    const result = parseStatement('Date,Description,Debit,Credit\n2026-09-10,Netflix,₹499,\n2026-09-11,Salary,,50000');
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({ merchant: 'Netflix', amount: 499 });
  });

  it('supports tab-separated bank exports', () => {
    const result = parseStatement('Transaction Date\tNarration\tAmount\n2026-09-12\tUPI grocery\t1,299');
    expect(result[0]).toMatchObject({ merchant: 'UPI grocery', amount: 1299 });
  });
});
