import { type NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  const locale = request.nextUrl.pathname === "/tr" || request.nextUrl.pathname.startsWith("/tr/")
    ? "tr"
    : "en";
  requestHeaders.set("x-ilaios-locale", locale);
  return NextResponse.next({ request: { headers: requestHeaders } });
}
