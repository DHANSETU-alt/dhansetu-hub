/** @type {import('./types/shakthi').ShakthiConfig | Record<string, unknown>} */
module.exports = {
  system: "ShakthiOS",
  service: "dhansetu-hub",
  domains: ["dhansetuhub.in", "www.dhansetuhub.in"],
  healthPath: "/api/health",
  paymentProvider: "razorpay",
  services: [
    { slug: "image-to-pdf", title: "Image to PDF", path: "/tools/image-to-pdf" },
    { slug: "budget-planner", title: "Budget Planner", path: "/tools/budget-planner" },
  ],
  dns: { correctRecords: [{ type: "CNAME", name: "@", content: "dhansetu-hub.onrender.com" }, { type: "CNAME", name: "www", content: "dhansetu-hub.onrender.com" }] },
  deployment: { platform: "render", bindHost: "0.0.0.0" },
  security: { headers: true, webhookSignature: "x-razorpay-signature" },
};
