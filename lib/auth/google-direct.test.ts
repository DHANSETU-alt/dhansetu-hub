import { describe, expect, it } from "vitest";
import { safeNextPath } from "./google-direct";

describe("direct Google OAuth safety helpers", () => {
  it("allows only internal single-slash destinations", () => {
    expect(safeNextPath("/checkout?tier=smartbudget_pro")).toBe("/checkout?tier=smartbudget_pro");
    expect(safeNextPath("//evil.example/login")).toBe("/");
    expect(safeNextPath("https://evil.example/login")).toBe("/");
    expect(safeNextPath(null)).toBe("/");
  });
});
