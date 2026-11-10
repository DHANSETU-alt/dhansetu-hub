import type { TierId } from "./tiers";

// All Access includes SmartBudget Pro. An existing Pro purchase can still upgrade.
export function purchaseCoversTier(purchased: TierId, requested: TierId) {
  return purchased === requested
    || ((purchased === "all_access" || purchased === "founder_pass") && requested === "smartbudget_pro")
    || (purchased === "founder_pass" && requested === "all_access");
}
