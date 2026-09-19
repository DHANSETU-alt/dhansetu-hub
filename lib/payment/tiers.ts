export const TIERS = {
  founding_lifetime: { label: "AI Starter Kit", amountPaise: 199900, currency: "INR", seatLimit: 100 },
  pro_lifetime: { label: "AI Agency Builder", amountPaise: 999900, currency: "INR", seatLimit: 250 },
  team_lifetime: { label: "Agency + Tools Combo", amountPaise: 1999900, currency: "INR", seatLimit: 50 },
} as const;

export type TierId = keyof typeof TIERS;
export const isTierId = (value: unknown): value is TierId =>
  typeof value === "string" && Object.prototype.hasOwnProperty.call(TIERS, value);
