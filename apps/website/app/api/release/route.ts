import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(
    {
      service: "ilaios-website",
      commitSha: process.env.VERCEL_GIT_COMMIT_SHA ?? null,
      deploymentId: process.env.VERCEL_DEPLOYMENT_ID ?? null,
      environment: process.env.VERCEL_ENV ?? process.env.VERCEL_TARGET_ENV ?? null,
      productionUrl: process.env.VERCEL_PROJECT_PRODUCTION_URL ?? null,
      branch: process.env.VERCEL_GIT_COMMIT_REF ?? null,
    },
    {
      headers: {
        "Cache-Control": "no-store, max-age=0",
      },
    },
  );
}
