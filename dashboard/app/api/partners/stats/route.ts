import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/partners/stats
 * Referral stats (clicks, conversions, revenue)
 *
 * Query params:
 * - email: partner email (required)
 * - period?: 'day' | 'week' | 'month' | 'all' (default: 'all')
 *
 * Returns: {
 *   total_clicks: number,
 *   total_conversions: number,
 *   conversion_rate: number (percent),
 *   total_revenue: number,
 *   total_earned_commission: number,
 *   total_paid_commission: number,
 *   pending_commission: number,
 *   period_start: string,
 *   period_end: string,
 *   top_products: [ { product, count, revenue } ]
 * }
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const email = searchParams.get('email');
    const period = searchParams.get('period') || 'all';

    if (!email) {
      return NextResponse.json(
        { error: 'Missing required query parameter: email' },
        { status: 400 }
      );
    }

    const validPeriods = ['day', 'week', 'month', 'all'];
    if (!validPeriods.includes(period)) {
      return NextResponse.json(
        { error: 'Invalid period. Must be one of: day, week, month, all' },
        { status: 400 }
      );
    }

    // Call Python backend
    const response = await fetch(
      `http://localhost:8000/api/partners/stats?email=${encodeURIComponent(email)}&period=${period}`
    );
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Partner stats error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
