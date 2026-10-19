import { createHmac, timingSafeEqual } from "node:crypto";

export function signPayload(payload: string, secret: string) {
  return createHmac("sha256", secret).update(payload).digest("hex");
}

export function verifySignature(payload: string, signature: string | null, secret: string) {
  if (!signature || !/^[a-f0-9]{64}$/i.test(signature)) return false;
  const expected = Buffer.from(signPayload(payload, secret), "hex");
  const actual = Buffer.from(signature, "hex");
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
