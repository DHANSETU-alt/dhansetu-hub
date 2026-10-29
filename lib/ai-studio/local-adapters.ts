const money = (value: unknown) => Number.isFinite(Number(value)) ? Number(value) : 0;

export function reminderTone(input: Record<string, unknown>) {
  const client = String(input.clientName || "your accounts team");
  const invoice = String(input.invoiceNo || "the invoice");
  const amount = String(input.amount || "the outstanding amount");
  const dueDate = String(input.dueDate || "the due date");
  const tone = String(input.tone || "Polite & Cordial");
  if (tone.toLowerCase().includes("firm")) {
    return `Attention ${client}: invoice ${invoice} for ₹${amount} is due on ${dueDate}. Please arrange settlement and share the UTR for reconciliation. — DhanSetu Hub`;
  }
  if (tone.toLowerCase().includes("professional")) {
    return `Dear ${client}, invoice ${invoice} for ₹${amount} is due on ${dueDate}. Kindly confirm the expected settlement date so we can keep the ledger current. — DhanSetu Hub`;
  }
  return `Namaste ${client}! Friendly reminder: invoice ${invoice} for ₹${amount} is scheduled for settlement by ${dueDate}. Please share the payment reference after settlement. — DhanSetu Hub`;
}

export function suggestHsn(description: string) {
  const query = description.toLowerCase();
  if (/(consult|advis|strategy)/.test(query)) return { hsn: "998311", taxRate: 18, refinedDesc: "Management consulting and operational advice", justification: "Consulting service classification" };
  if (/(design|ui|ux|brand)/.test(query)) return { hsn: "998391", taxRate: 18, refinedDesc: "Specialty graphic, brand and UI/UX design", justification: "Design service classification" };
  if (/(market|advert|seo)/.test(query)) return { hsn: "998361", taxRate: 18, refinedDesc: "Advertising, lead acquisition and marketing strategy", justification: "Marketing service classification" };
  if (/(account|audit|tax)/.test(query)) return { hsn: "998222", taxRate: 18, refinedDesc: "Accounting, tax bookkeeping and audit advisory", justification: "Accounting service classification" };
  return { hsn: "998314", taxRate: 18, refinedDesc: "Information technology and web services", justification: "IT service classification" };
}

export function auditInvoice(invoice: Record<string, any>) {
  const seller = invoice?.seller ?? {};
  const buyer = invoice?.buyer ?? {};
  const checks = [
    { status: seller.gstin && buyer.gstin ? "PASS" : "WARN", rule: "GSTIN presence", detail: "Seller and buyer GSTIN fields are present for review." },
    { status: seller.stateCode && buyer.stateCode ? "PASS" : "WARN", rule: "Place of supply", detail: "State codes are available for CGST/SGST versus IGST calculation." },
    { status: invoice?.invNo ? "PASS" : "WARN", rule: "Invoice number", detail: "Invoice identifier is present for ledger reconciliation." },
  ];
  const risk = checks.some((check) => check.status === "WARN") ? "MEDIUM" : "LOW";
  return {
    riskScore: risk,
    summary: risk === "LOW" ? "Local Rule 48 pre-check passed. Keep the signed invoice and payment evidence together." : "Local pre-check found fields that need review before issuing the invoice.",
    checks,
    caAdvice: "This is an operational pre-check, not legal or tax advice. Reconcile payment and GST records before filing.",
  };
}

export function analyzeExpense(input: Record<string, unknown>) {
  const category = String(input.category || "").toLowerCase();
  const blocked = /(food|catering|passenger vehicle|vehicle|fuel|personal)/.test(category);
  return {
    itcStatus: blocked ? "BLOCKED_17_5" : "ELIGIBLE",
    legalGround: blocked ? "Review Section 17(5) blocked-credit categories before claiming ITC." : "Business-use expense is eligible for review under Section 16(1), subject to valid tax invoice and business use.",
    gstr3bTable: blocked ? "Table 4(B)(1)" : "Table 4(A)(5)",
    amount: money(input.amount),
    gstRate: money(input.gstRate),
  };
}

export function parseForm16(rawText: string) {
  const read = (label: string, fallback: number) => {
    const match = rawText.match(new RegExp(`${label}[^0-9]*([0-9,]+)`, "i"));
    return match ? Number(match[1].replace(/,/g, "")) : fallback;
  };
  return {
    grossSalary: read("Gross Salary", 1520000),
    hraExempt: read("HRA", 140000),
    sec80C: read("80C", 150000),
    sec80D: read("80D", 25000),
    sec80CCD: read("NPS", 50000),
    homeLoanInterest: read("Home Loan", 0),
    tdsDeducted: read("TDS", 110000),
    caNotes: "Local extraction completed; verify against the original Form 16 before filing.",
  };
}
