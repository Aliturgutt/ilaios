import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Use ILAIOS - ILAIOS",
  description: "ILAIOS'u yönetilen yapay zeka işlemleri için nasıl kullanacağınızı öğrenin.",
  alternates: {
    canonical: "/use-ilaios",
    languages: {
      en: "/use-ilaios",
      tr: "/tr/use-ilaios",
      'x-default': "/use-ilaios",
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
