import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.text();

  const upstream = await fetch(`${BACKEND_BASE_URL}/api/v1/auth/register/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body,
    cache: "no-store",
  });

  const contentType =
    upstream.headers.get("content-type") ?? "application/json";
  const requestId = upstream.headers.get("X-Request-ID");
  const responseBody = await upstream.text();

  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: {
      "Content-Type": contentType,
      ...(requestId ? { "X-Request-ID": requestId } : {}),
    },
  });
}
