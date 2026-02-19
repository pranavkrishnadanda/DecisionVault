import { type NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ integrationId: string }> },
) {
  const { integrationId } = await params;
  const authHeader = request.headers.get("authorization");
  const upstreamUrl = new URL(
    `/api/v1/integrations/${integrationId}/slack/install-url/`,
    BACKEND_BASE_URL,
  );

  const configuredRedirectUri =
    process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI?.trim() ?? "";

  request.nextUrl.searchParams.forEach((value, key) => {
    if (key !== "redirect_uri") {
      upstreamUrl.searchParams.set(key, value);
      return;
    }

    const shouldOverrideWithConfigured =
      configuredRedirectUri.length > 0 &&
      (value.trim().length === 0 || value.startsWith("http://localhost"));

    upstreamUrl.searchParams.set(
      key,
      shouldOverrideWithConfigured ? configuredRedirectUri : value,
    );
  });

  const upstream = await fetch(upstreamUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    cache: "no-store",
  });

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
