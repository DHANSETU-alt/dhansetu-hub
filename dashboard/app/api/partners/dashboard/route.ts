import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/partners/dashboard
 * Partner dashboard data (commissions, payouts, stats)
 *
 * Query params:
 * - email: partner email (required)
 *
 * Returns: {
 *   partner: { id, name, email, tier, status, commission_rate, ... },
 *   stats: { total_clicks, total_conversions, conversion_rate, total_revenue, ... },
 *   recent_commissions: [ { id, transaction_id, amount, commission_amount, ... } ],
 *   recent_payouts: [ { id, total_amount, status, period_start, period_end, ... } ]
 * }
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const email = searchParams.get('email');

    if (!email) {
      return NextResponse.json(
        { error: 'Missing required query parameter: email' },
        { status: 400 }
      );
    }

    // Call Python backend
    const response = await fetch(`http://localhost:8000/api/partners/dashboard?email=${encodeURIComponent(email)}`);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Partner dashboard error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
