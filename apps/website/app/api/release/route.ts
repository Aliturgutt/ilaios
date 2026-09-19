import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ release: "1.0.0" });
}
