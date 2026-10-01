import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/partners/commissions
 * Commission history with filters
 *
 * Query params:
 * - email: partner email (required)
 * - status?: 'earned' | 'paid' | 'disputed' | 'refunded'
 * - limit?: number (default: 100)
 * - offset?: number (default: 0)
 *
 * Returns: {
 *   commissions: [
 *     {
 *       id, partner_id, transaction_id, customer_email, amount,
 *       commission_rate, commission_amount, product, status, paid_date, created_at
 *     }
 *   ],
 *   total: number
 * }
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const email = searchParams.get('email');
    const status = searchParams.get('status');
    const limit = parseInt(searchParams.get('limit') || '100');
    const offset = parseInt(searchParams.get('offset') || '0');

    if (!email) {
      return NextResponse.json(
        { error: 'Missing required query parameter: email' },
        { status: 400 }
      );
    }

    // Build query string
    const params = new URLSearchParams({ email });
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    // Call Python backend
    const response = await fetch(`http://localhost:8000/api/partners/commissions?${params.toString()}`);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Partner commissions error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
