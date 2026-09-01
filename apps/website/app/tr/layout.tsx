import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { default: "ILAIOS Türkiye", template: "%s" },
  description: "ILAIOS; kontrollü akıllı otomasyon, doğrulanabilir yürütme ve güvenlik odaklı operasyonlar için altyapı geliştirir.",
};

export default function TurkishLayout({ children }: { children: React.ReactNode }) {
  return children;
}
