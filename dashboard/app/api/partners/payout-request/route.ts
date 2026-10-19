import { NextRequest, NextResponse } from 'next/server';

/**
 * POST /api/partners/payout-request
 * Partner requests payout for earned commissions
 *
 * Request body:
 * {
 *   email: string,
 *   payout_method: 'bank_transfer' | 'paypal' | 'upi',
 *   bank_details?: { account_number, ifsc, beneficiary_name },
 *   upi_id?: string,
 *   paypal_email?: string
 * }
 *
 * Returns: { id, partner_id, total_amount, payout_method, status: 'pending' }
 *
 * Errors:
 * - "Minimum payout amount is ₹100" (if earned < 100)
 * - "Payout request already pending" (if one exists)
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      email,
      payout_method,
      bank_details,
      upi_id,
      paypal_email,
    } = body;

    // Validation
    if (!email || !payout_method) {
      return NextResponse.json(
        { error: 'Missing required fields: email, payout_method' },
        { status: 400 }
      );
    }

    const validMethods = ['bank_transfer', 'paypal', 'upi'];
    if (!validMethods.includes(payout_method)) {
      return NextResponse.json(
        { error: 'Invalid payout_method. Must be one of: bank_transfer, paypal, upi' },
        { status: 400 }
      );
    }

    // Method-specific validation
    if (payout_method === 'bank_transfer' && !bank_details) {
      return NextResponse.json(
        { error: 'bank_details required for bank_transfer method' },
        { status: 400 }
      );
    }
    if (payout_method === 'upi' && !upi_id) {
      return NextResponse.json(
        { error: 'upi_id required for upi method' },
        { status: 400 }
      );
    }
    if (payout_method === 'paypal' && !paypal_email) {
      return NextResponse.json(
        { error: 'paypal_email required for paypal method' },
        { status: 400 }
      );
    }

    // Call Python backend
    const response = await fetch('http://localhost:8000/api/partners/payout-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        payout_method,
        bank_details: bank_details || null,
        upi_id: upi_id || null,
        paypal_email: paypal_email || null,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error('Payout request error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
