import type { Metadata } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  title: "Use ILAIOS",
  description: "Learn how to use ILAIOS for governed AI operations.",
  canonical: `${siteUrl}/use-ilaios`,
  alternates: {
    languages: {
      en: `${siteUrl}/use-ilaios`,
      tr: `${siteUrl}/tr/use-ilaios`,
      'x-default': `${siteUrl}/use-ilaios`,
    },
  },
};

export default function UseILAIOSPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-[var(--text)] p-4">
      <div className="max-w-md w-full space-y-6">
        <h1 className="text-3xl font-bold">Use ILAIOS</h1>
        <p className="text-[var(--muted)]">Learn how to use ILAIOS for governed AI operations.</p>
      </div>
    </main>
  );
}
