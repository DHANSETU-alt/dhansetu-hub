export const TIERS = {
  smartbudget_pro: { label: "SmartBudget Pro", amountPaise: 14900, currency: "INR", seatLimit: 10000 },
  all_access: { label: "DhanSetu All Access", amountPaise: 39900, currency: "INR", seatLimit: 10000 },
  founding_lifetime: { label: "AI Starter Kit", amountPaise: 199900, currency: "INR", seatLimit: 100 },
  pro_lifetime: { label: "AI Agency Builder", amountPaise: 999900, currency: "INR", seatLimit: 250 },
  team_lifetime: { label: "Agency + Tools Combo", amountPaise: 1999900, currency: "INR", seatLimit: 50 },
} as const;

export const PUBLIC_TIERS = {
  smartbudget_pro: TIERS.smartbudget_pro,
  all_access: TIERS.all_access,
} as const;

export const PUBLIC_PLANS = {
  free: { label: "Free workspace", amountPaise: 0, currency: "INR" },
  ...PUBLIC_TIERS,
} as const;

export type TierId = keyof typeof TIERS;
export const isTierId = (value: unknown): value is TierId =>
  typeof value === "string" && Object.prototype.hasOwnProperty.call(TIERS, value);
