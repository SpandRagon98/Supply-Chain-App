import { NextRequest, NextResponse } from "next/server";

const apiUrl = process.env.API_URL ?? "http://localhost:8000/api/v1";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstream = new URL(`${apiUrl}/${path.join("/")}`);
  upstream.search = request.nextUrl.search;
  const headers = new Headers({ "Content-Type": "application/json" });
  for (const name of ["authorization", "x-organization-id", "x-user-id", "x-request-id"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (process.env.INTERNAL_API_TOKEN) headers.set("X-Internal-API-Token", process.env.INTERNAL_API_TOKEN);
  if (process.env.DEFAULT_ORGANIZATION_ID) headers.set("X-Organization-ID", process.env.DEFAULT_ORGANIZATION_ID);
  if (process.env.DEFAULT_USER_ID) headers.set("X-User-ID", process.env.DEFAULT_USER_ID);
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  try {
    const response = await fetch(upstream, { method: request.method, headers, body, cache: "no-store" });
    return new NextResponse(response.body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: { code: "backend_unavailable", message: "The backend is unavailable." } },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
