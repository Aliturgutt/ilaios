import type { Metadata } from "next";
import ProductDeepDive from "../../ProductDeepDive";
export const metadata: Metadata = { title: "Kurumlar İçin", description: "ILAIOS'un kurumlara otomasyon, yazılım, araştırma, medya ve güvenlik işlerinde nasıl yardımcı olduğunu inceleyin.", alternates: { canonical: "/tr/enterprise", languages: { tr: "/tr/enterprise", en: "/enterprise", "x-default": "/enterprise" } } };
export default function Page(){ return <ProductDeepDive locale="tr" mode="enterprise" />; }
