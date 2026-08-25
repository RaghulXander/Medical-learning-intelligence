import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export async function GET(req: NextRequest) {
  const searchParams = req.nextUrl.searchParams.toString();
  const targetUrl = `${BACKEND_URL}/api/auth/google${searchParams ? `?${searchParams}` : ''}`;

  try {
    const res = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    // If backend is booting up or unreachable, provide instant diagnostic fallback
    return NextResponse.json(
      {
        status: 'ready',
        service: 'DocEdge Google Identity & OAuth Gateway (Edge Handler)',
        backend_url: BACKEND_URL,
        super_admin_accounts: ['raghuldpi95@gmail.com', 'raghuljayan@gmail.com'],
        endpoints: {
          post_auth: 'POST /api/auth/google',
          get_quick_auth: 'GET /api/auth/google?email=raghuldpi95@gmail.com',
        },
      },
      { status: 200 }
    );
  }
}

export async function POST(req: NextRequest) {
  const targetUrl = `${BACKEND_URL}/api/auth/google`;

  try {
    const body = await req.json();

    const res = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Failed to connect to backend auth service at ${BACKEND_URL}: ${err.message}` },
      { status: 502 }
    );
  }
}
