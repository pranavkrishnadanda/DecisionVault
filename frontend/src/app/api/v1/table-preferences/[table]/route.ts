import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

interface RouteParams {
  params: Promise<{
    table: string;
  }>;
}

export async function GET(request: NextRequest, context: RouteParams) {
  const { table } = await context.params;
  const authHeader = request.headers.get("authorization");

  const upstream = await fetch(
    `${BACKEND_BASE_URL}/api/v1/table-preferences/${table}/`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
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

export async function PUT(request: NextRequest, context: RouteParams) {
  const { table } = await context.params;
  const authHeader = request.headers.get("authorization");
  const body = await request.text();

  const upstream = await fetch(
    `${BACKEND_BASE_URL}/api/v1/table-preferences/${table}/`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body,
      cache: "no-store",
    },
  );

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
