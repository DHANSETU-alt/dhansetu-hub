export const TIERS = {
  founding_lifetime: { label: "Founding Lifetime", amountPaise: 9900, currency: "INR", seatLimit: 100 },
  pro_lifetime: { label: "Pro Lifetime", amountPaise: 49900, currency: "INR", seatLimit: 250 },
  team_lifetime: { label: "Team Lifetime", amountPaise: 149900, currency: "INR", seatLimit: 50 },
} as const;

export type TierId = keyof typeof TIERS;
export const isTierId = (value: unknown): value is TierId =>
  typeof value === "string" && Object.prototype.hasOwnProperty.call(TIERS, value);
