import { spawn } from "node:child_process";
import { signPayload } from "../lib/payment/signatures";

const port = 3457;
const base = `http://127.0.0.1:${port}`;
const keySecret = "local_key_secret_for_payment_harness";
const webhookSecret = "local_webhook_secret_for_payment_harness";
let passed = 0;

function assert(condition: unknown, name: string) {
  if (!condition) throw new Error(`FAIL: ${name}`);
  passed += 1; console.log(`PASS ${passed}: ${name}`);
}

async function waitForServer() {
  for (let i = 0; i < 60; i += 1) {
    try { if ((await fetch(base)).ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Local Next.js server did not become ready");
}

async function create(user: string, tier = "founding_lifetime") {
  const response = await fetch(`${base}/api/checkout/create-order`, { method: "POST", headers: { "content-type": "application/json", "x-test-user-id": user }, body: JSON.stringify({ tier, consent: true }) });
  const body = await response.json();
  if (!response.ok) throw new Error(`Create order failed: ${JSON.stringify(body)}`);
  return body as { orderId: string };
}

async function verify(user: string, orderId: string, paymentId: string, signature = signPayload(`${orderId}|${paymentId}`, keySecret)) {
  return fetch(`${base}/api/checkout/verify`, { method: "POST", headers: { "content-type": "application/json", "x-test-user-id": user }, body: JSON.stringify({ razorpay_order_id: orderId, razorpay_payment_id: paymentId, razorpay_signature: signature }) });
}

async function webhook(orderId: string, paymentId: string) {
  const raw = JSON.stringify({ event: "payment.captured", payload: { payment: { entity: { id: paymentId, order_id: orderId } } } });
  return fetch(`${base}/api/webhooks/razorpay`, { method: "POST", headers: { "content-type": "application/json", "x-razorpay-signature": signPayload(raw, webhookSecret) }, body: raw });
}

async function main() {
const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", "-p", String(port)], {
  cwd: process.cwd(), stdio: ["ignore", "pipe", "pipe"],
  env: { ...process.env, PAYMENT_FLOW_TEST_MODE: "1", RAZORPAY_KEY_ID: "rzp_test_harness", RAZORPAY_KEY_SECRET: keySecret, RAZORPAY_WEBHOOK_SECRET: webhookSecret, NEXT_PUBLIC_SUPABASE_URL: "http://127.0.0.1:54321", NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key", SUPABASE_SERVICE_ROLE_KEY: "test-service-key", NEXT_PUBLIC_APP_URL: `${base}/app` },
});
let serverLog = "";
child.stdout.on("data", (chunk) => { serverLog += chunk.toString(); });
child.stderr.on("data", (chunk) => { serverLog += chunk.toString(); });

try {
  await waitForServer();
  await fetch(`${base}/api/test/payment-state`, { method: "DELETE" });

  const unauth = await fetch(`${base}/api/checkout/create-order`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ tier: "founding_lifetime", consent: true }) });
  assert(unauth.status === 401, "unauthenticated order creation is rejected");

  const first = await create("user-valid");
  const valid = await verify("user-valid", first.orderId, "pay_valid");
  const validBody = await valid.clone().text();
  assert(valid.status === 200, `valid signed payment grants entitlement (status ${valid.status}: ${validBody})`);
  const duplicate = await webhook(first.orderId, "pay_valid");
  assert(duplicate.status === 200, "duplicate webhook is accepted idempotently");
  const stateAfterDuplicate = await (await fetch(`${base}/api/test/payment-state`)).json();
  assert(stateAfterDuplicate.purchases.filter((p: { status: string }) => p.status === "paid").length === 1 && stateAfterDuplicate.seats.founding_lifetime === 1, "duplicate delivery grants exactly once");

  const tamperedSignature = await verify("user-valid", first.orderId, "pay_wrong", "0".repeat(64));
  assert(tamperedSignature.status === 400, "tampered payment signature is rejected");

  const badAmount = await create("user-amount");
  await fetch(`${base}/api/test/payment-state`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ orderId: badAmount.orderId, amount: 1 }) });
  assert((await verify("user-amount", badAmount.orderId, "pay_bad_amount")).status === 422, "tampered amount is rejected");

  const badTier = await create("user-tier");
  await fetch(`${base}/api/test/payment-state`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ orderId: badTier.orderId, tier: "pro_lifetime" }) });
  assert((await verify("user-tier", badTier.orderId, "pay_bad_tier")).status === 422, "tampered tier is rejected");

  await fetch(`${base}/api/test/payment-state`, { method: "DELETE" });
  const orders = await Promise.all(Array.from({ length: 51 }, (_, index) => create(`seat-user-${index}`, "team_lifetime")));
  const results = await Promise.all(orders.map((order, index) => verify(`seat-user-${index}`, order.orderId, `pay_seat_${index}`)));
  const successes = results.filter((response) => response.status === 200).length;
  const seatState = await (await fetch(`${base}/api/test/payment-state`)).json();
  assert(successes === 50 && seatState.seats.team_lifetime === 50, "concurrent purchases never exceed the seat limit");

  console.log(`\nPayment flow regression guard: ${passed}/8 assertions passed.`);
} catch (error) {
  console.error(serverLog.slice(-5000)); throw error;
} finally {
  child.kill("SIGTERM");
}
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
