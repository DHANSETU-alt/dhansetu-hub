import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/partners/referral-link
 * Get partner's unique referral link and tracking info
 *
 * Query params:
 * - email: partner email (required)
 *
 * Returns: {
 *   referral_link: string,
 *   tracking_param: string,
 *   share_text: string,
 *   share_urls: {
 *     twitter: string,
 *     linkedin: string,
 *     whatsapp: string
 *   }
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
    const response = await fetch(`http://localhost:8000/api/partners/referral-link?email=${encodeURIComponent(email)}`);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Referral link error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
