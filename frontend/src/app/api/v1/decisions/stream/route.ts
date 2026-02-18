import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization");

  const upstream = await fetch(`${BACKEND_BASE_URL}/api/v1/decisions/stream/`, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    cache: "no-store",
  });

  if (!upstream.body) {
    return NextResponse.json(
      { detail: "Decision stream unavailable" },
      { status: 502 },
    );
  }

  const requestId = upstream.headers.get("X-Request-ID");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream",
      ...(requestId ? { "X-Request-ID": requestId } : {}),
    },
  });
}
