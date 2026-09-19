import type { Metadata } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  title: "Use ILAIOS - ILAIOS",
  description: "ILAIOS'u yönetilen yapay zeka işlemleri için nasıl kullanacağınızı öğrenin.",
  canonical: `${siteUrl}/tr/use-ilaios`,
  alternates: {
    languages: {
      en: `${siteUrl}/use-ilaios`,
      tr: `${siteUrl}/tr/use-ilaios`,
      'x-default': `${siteUrl}/use-ilaios`,
    },
  },
};

export default function TrUseILAIOSPage() {
  return (
    <main>
      <h1>Use ILAIOS</h1>
      <p>How to use ILAIOS placeholder (Turkish).</p>
    </main>
  );
}
