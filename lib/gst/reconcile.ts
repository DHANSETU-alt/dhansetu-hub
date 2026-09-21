export type GstInvoice = { invoiceNumber: string; supplierGstin: string; taxableValuePaise: number; taxPaise: number };
export type GstReview = { invoiceNumber: string; supplierGstin: string; reason: "missing_in_2b" | "missing_in_register" | "duplicate" | "value_mismatch"; registerTaxPaise: number; statementTaxPaise: number };
export type GstReconciliation = { matched: number; review: GstReview[]; amountRequiringReviewPaise: number; note: string };

const key = (item: Pick<GstInvoice, "invoiceNumber" | "supplierGstin">) => `${item.supplierGstin.trim().toUpperCase()}|${item.invoiceNumber.trim().toUpperCase()}`;

export function reconcileGst(register: GstInvoice[], statement: GstInvoice[]): GstReconciliation {
  const registerMap = new Map<string, GstInvoice[]>(); const statementMap = new Map<string, GstInvoice[]>();
  for (const item of register) registerMap.set(key(item), [...(registerMap.get(key(item)) ?? []), item]);
  for (const item of statement) statementMap.set(key(item), [...(statementMap.get(key(item)) ?? []), item]);
  const review: GstReview[] = [];
  for (const [invoiceKey, rows] of Array.from(registerMap.entries())) {
    const [supplierGstin, invoiceNumber] = invoiceKey.split("|"); const matches = statementMap.get(invoiceKey) ?? [];
    if (rows.length > 1 || matches.length > 1) { review.push({ invoiceNumber, supplierGstin, reason: "duplicate", registerTaxPaise: rows.reduce((sum: number, row: GstInvoice) => sum + row.taxPaise, 0), statementTaxPaise: matches.reduce((sum: number, row: GstInvoice) => sum + row.taxPaise, 0) }); continue; }
    if (!matches.length) { review.push({ invoiceNumber, supplierGstin, reason: "missing_in_2b", registerTaxPaise: rows[0].taxPaise, statementTaxPaise: 0 }); continue; }
    if (rows[0].taxableValuePaise !== matches[0].taxableValuePaise || rows[0].taxPaise !== matches[0].taxPaise) { review.push({ invoiceNumber, supplierGstin, reason: "value_mismatch", registerTaxPaise: rows[0].taxPaise, statementTaxPaise: matches[0].taxPaise }); }
  }
  for (const [invoiceKey, rows] of Array.from(statementMap.entries())) if (!registerMap.has(invoiceKey)) { const [supplierGstin, invoiceNumber] = invoiceKey.split("|"); review.push({ invoiceNumber, supplierGstin, reason: "missing_in_register", registerTaxPaise: 0, statementTaxPaise: rows.reduce((sum: number, row: GstInvoice) => sum + row.taxPaise, 0) }); }
  const matched = registerMap.size - review.filter((item) => item.reason !== "missing_in_register").length;
  return { matched: Math.max(0, matched), review, amountRequiringReviewPaise: review.reduce((sum, item) => sum + Math.max(item.registerTaxPaise, item.statementTaxPaise), 0), note: "Review amount only. DhanSetu does not guarantee recoverable ITC or perform GST filing." };
}
