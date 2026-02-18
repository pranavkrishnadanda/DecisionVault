import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ decisionId: string }> },
) {
  const { decisionId } = await params;
  const authHeader = request.headers.get("authorization");

  const upstream = await fetch(
    `${BACKEND_BASE_URL}/api/v1/decisions/${decisionId}/retry/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: await request.text(),
      cache: "no-store",
    },
  );

  const contentType =
    upstream.headers.get("content-type") ?? "application/json";
  const requestId = upstream.headers.get("X-Request-ID");
  const body = await upstream.text();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": contentType,
      ...(requestId ? { "X-Request-ID": requestId } : {}),
    },
  });
}
