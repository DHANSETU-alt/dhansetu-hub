import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function GET() {
  const required = [
    'NEXT_PUBLIC_SUPABASE_URL',
    'NEXT_PUBLIC_SUPABASE_ANON_KEY',
    'SUPABASE_SERVICE_ROLE_KEY',
    'RAZORPAY_KEY_ID',
    'RAZORPAY_KEY_SECRET',
    'RAZORPAY_WEBHOOK_SECRET',
  ];
  const configuration = Object.fromEntries(required.map((name) => [name, Boolean(process.env[name])]));
  const paymentReady = configuration.SUPABASE_SERVICE_ROLE_KEY
    && configuration.RAZORPAY_KEY_ID
    && configuration.RAZORPAY_KEY_SECRET
    && configuration.RAZORPAY_WEBHOOK_SECRET;
  return NextResponse.json({
    status: 'ok',
    service: 'dhansetu-hub',
    timestamp: new Date().toISOString(),
    paymentReady,
    configuration,
  }, { headers: { 'Cache-Control': 'no-store' } });
}
