import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { default: "ILAIOS Türkiye", template: "%s | ILAIOS" },
  description: "ILAIOS; kontrollü akıllı otomasyon, doğrulanabilir yürütme ve güvenlik odaklı operasyonlar için altyapı geliştirir.",
  alternates: { canonical: "/tr", languages: { tr: "/tr", en: "/", "x-default": "/" } },
};

export default function TurkishLayout({ children }: { children: React.ReactNode }) {
  return children;
}
