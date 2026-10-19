/** @type {import('./types/shakthi').ShakthiConfig | Record<string, unknown>} */
module.exports = {
  system: "ShakthiOS",
  service: "dhansetu-hub",
  domains: ["dhansetuhub.in", "www.dhansetuhub.in"],
  healthPath: "/api/health",
  paymentProvider: "razorpay",
  deployment: { platform: "render", bindHost: "0.0.0.0" },
  security: { headers: true, webhookSignature: "x-razorpay-signature" },
};
