import { afterEach, describe, expect, it, vi } from "vitest";
import { syncFounderSheet } from "./founder-sheets";

describe("founder Sheets boundary", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("fails closed when the private spreadsheet is not configured", async () => {
    vi.stubEnv("GOOGLE_SHEETS_SPREADSHEET_ID", "");
    vi.stubEnv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "");
    await expect(syncFounderSheet({
      gross: 0,
      cost: 0,
      commission: 0,
      net: 0,
      paidOrders: 0,
      customers: 0,
      transactionCount: 0,
      warnings: [],
    })).rejects.toThrow("spreadsheet ID is not configured");
  });
});
