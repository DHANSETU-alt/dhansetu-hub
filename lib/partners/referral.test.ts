import { describe, expect, it } from "vitest";
import {
  normaliseReferralCode,
  qualifiesForCommission,
  recordEligibleCommission,
} from "./referral";

describe("normaliseReferralCode", () => {
  it("accepts an issued code", () => {
    expect(normaliseReferralCode("abc123xy")).toBe("abc123xy");
  });

  it("trims surrounding whitespace", () => {
    expect(normaliseReferralCode("  abc123xy  ")).toBe("abc123xy");
  });

  it("rejects empty and missing values", () => {
    expect(normaliseReferralCode("")).toBeNull();
    expect(normaliseReferralCode(null)).toBeNull();
    expect(normaliseReferralCode(undefined)).toBeNull();
  });

  it("rejects codes carrying SQL or path characters", () => {
    expect(normaliseReferralCode("abc'; drop table--")).toBeNull();
    expect(normaliseReferralCode("../../etc/passwd")).toBeNull();
    expect(normaliseReferralCode("abc%20xy")).toBeNull();
  });

  it("rejects codes outside the issued length range", () => {
    expect(normaliseReferralCode("ab")).toBeNull();
    expect(normaliseReferralCode("a".repeat(33))).toBeNull();
  });
});

describe("qualifiesForCommission", () => {
  const base = { purchaseStatus: "paid", amountPaise: 14900, referralCode: "abc123xy" };

  it("qualifies a settled purchase carrying a valid code", () => {
    expect(qualifiesForCommission(base)).toBe(true);
  });

  it("refuses a purchase that is not yet paid", () => {
    expect(qualifiesForCommission({ ...base, purchaseStatus: "created" })).toBe(false);
    expect(qualifiesForCommission({ ...base, purchaseStatus: "failed" })).toBe(false);
  });

  it("refuses a purchase with no referral", () => {
    expect(qualifiesForCommission({ ...base, referralCode: null })).toBe(false);
  });

  it("refuses a zero or negative amount", () => {
    expect(qualifiesForCommission({ ...base, amountPaise: 0 })).toBe(false);
    expect(qualifiesForCommission({ ...base, amountPaise: -14900 })).toBe(false);
  });
});

type StubResult = { data: unknown; error: unknown };

function stubSupabase(select: StubResult, insert: StubResult = { data: null, error: null }) {
  const inserted: unknown[] = [];
  const client = {
    from: () => ({
      select: () => ({ eq: () => ({ eq: () => ({ maybeSingle: async () => select }) }) }),
      insert: async (row: unknown) => {
        inserted.push(row);
        return insert;
      },
    }),
  };
  return { client: client as never, inserted };
}

describe("recordEligibleCommission", () => {
  const params = { purchaseId: "purchase-1", partnerId: "partner-1" };

  it("records an eligible event when none exists", async () => {
    const { client, inserted } = stubSupabase({ data: null, error: null });
    await expect(recordEligibleCommission(client, params)).resolves.toBe("recorded");
    expect(inserted).toEqual([
      { partner_id: "partner-1", purchase_id: "purchase-1", event_type: "eligible" },
    ]);
  });

  it("does not credit the same purchase twice on a webhook retry", async () => {
    const { client, inserted } = stubSupabase({ data: { id: "existing" }, error: null });
    await expect(recordEligibleCommission(client, params)).resolves.toBe("already_recorded");
    expect(inserted).toEqual([]);
  });

  it("reports failure instead of crediting when the lookup errors", async () => {
    const { client, inserted } = stubSupabase({ data: null, error: { message: "boom" } });
    await expect(recordEligibleCommission(client, params)).resolves.toBe("failed");
    expect(inserted).toEqual([]);
  });
});
