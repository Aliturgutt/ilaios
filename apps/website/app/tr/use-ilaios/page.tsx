import type { Metadata } from "next";
import UseILAIOSPage from "../../UseILAIOSPage";

export const metadata: Metadata = {
  title: "ILAIOS'u Kullan",
  description: "ILAIOS'a ne sağlayabileceğinizi, neler oluşturabileceğinizi, yönetilen execution akışını, güncel factory readiness seviyelerini ve kabul edilen sonuçlarla gelen evidence modelini öğrenin.",
  alternates: { canonical: "/tr/use-ilaios", languages: { tr: "/tr/use-ilaios", en: "/use-ilaios", "x-default": "/use-ilaios" } },
};

export default function Page() { return <UseILAIOSPage locale="tr" />; }
