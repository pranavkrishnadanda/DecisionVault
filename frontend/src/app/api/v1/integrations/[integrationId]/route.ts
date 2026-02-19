import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

async function proxyIntegrationDetailRequest(
  request: NextRequest,
  method: "PATCH" | "DELETE",
  params: Promise<{ integrationId: string }>,
  body?: string,
) {
  const { integrationId } = await params;
  const authHeader = request.headers.get("authorization");

  const upstream = await fetch(
    `${BACKEND_BASE_URL}/api/v1/integrations/${integrationId}/`,
    {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      ...(typeof body === "string" ? { body } : {}),
      cache: "no-store",
    },
  );

  const contentType =
    upstream.headers.get("content-type") ?? "application/json";
  const requestId = upstream.headers.get("X-Request-ID");
  const upstreamBody = await upstream.text();
  const isNoBodyStatus =
    upstream.status === 204 ||
    upstream.status === 205 ||
    upstream.status === 304;

  return new NextResponse(isNoBodyStatus ? null : upstreamBody, {
    status: upstream.status,
    headers: {
      ...(!isNoBodyStatus ? { "Content-Type": contentType } : {}),
      ...(requestId ? { "X-Request-ID": requestId } : {}),
    },
  });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ integrationId: string }> },
) {
  const body = await request.text();

  return proxyIntegrationDetailRequest(request, "PATCH", params, body);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ integrationId: string }> },
) {
  return proxyIntegrationDetailRequest(request, "DELETE", params);
}
