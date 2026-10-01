import { NextRequest, NextResponse } from 'next/server';

/**
 * POST /api/partners/apply
 * Partner application submission
 *
 * Request body:
 * {
 *   business_id: number,
 *   name: string,
 *   email: string,
 *   phone?: string,
 *   company?: string,
 *   website?: string,
 *   tier: 'affiliate' | 'reseller' | 'agency'
 * }
 *
 * Returns: { id, name, email, tier, commission_rate, referral_link, status: 'pending' }
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { business_id, name, email, phone, company, website, tier = 'affiliate' } = body;

    // Validation
    if (!business_id || !name || !email) {
      return NextResponse.json(
        { error: 'Missing required fields: business_id, name, email' },
        { status: 400 }
      );
    }

    const validTiers = ['affiliate', 'reseller', 'agency'];
    if (!validTiers.includes(tier)) {
      return NextResponse.json(
        { error: 'Invalid tier. Must be one of: affiliate, reseller, agency' },
        { status: 400 }
      );
    }

    // Call Python backend
    const response = await fetch('http://localhost:8000/api/partners/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_id,
        name,
        email,
        phone: phone || null,
        company: company || null,
        website: website || null,
        tier,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error('Partner apply error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
