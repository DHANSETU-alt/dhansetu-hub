import { NextResponse } from 'next/server';
import { razorpayLive } from '@/lib/razorpay-live';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  const payment = razorpayLive();
  const paymentEndpoint = '/api/payment/verify-live';
  return NextResponse.json({
    status: 'ok',
    service: 'dhansetu-hub',
    timestamp: new Date().toISOString(),
    origin: 200,
    paymentReady: payment.live,
    paymentEndpoint,
    paymentEndpointStatus: payment.live ? 200 : 503,
    webhookSignatureVerified: payment.webhookSignature,
  }, { headers: { 'Cache-Control': 'no-store' } });
}
