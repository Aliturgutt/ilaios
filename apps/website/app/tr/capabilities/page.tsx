import type { Metadata } from "next";
import ProductDeepDive from "../../ProductDeepDive";
export const metadata: Metadata = { title: "Yetenekler", description: "ILAIOS'un kontrollü otomasyon, yazılım, web, medya, araştırma, zekâ ve güvenlik yeteneklerini inceleyin.", alternates: { canonical: "/tr/capabilities", languages: { tr: "/tr/capabilities", en: "/capabilities", "x-default": "/capabilities" } } };
export default function Page(){ return <ProductDeepDive locale="tr" mode="capabilities" />; }
