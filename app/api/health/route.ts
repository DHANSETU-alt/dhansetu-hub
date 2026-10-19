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
    paymentReady: payment.configured,
    paymentEndpoint,
    paymentEndpointStatus: payment.configured ? 200 : 503,
    paymentMode: payment.mode,
    transactionVerified: payment.transactionVerified,
    webhookSecretConfigured: payment.webhookSecretConfigured,
  }, { headers: { 'Cache-Control': 'no-store' } });
}
