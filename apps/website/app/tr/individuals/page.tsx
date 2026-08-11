import type { Metadata } from "next";
import ProductDeepDive from "../../ProductDeepDive";
export const metadata: Metadata = { title: "Bireysel Kullanıcılar İçin", description: "ILAIOS'un bireysel otomasyon, araştırma, yazılım, web ve medya işlerinde nasıl kullanılabileceğini inceleyin.", alternates: { canonical: "/tr/individuals", languages: { tr: "/tr/individuals", en: "/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <ProductDeepDive locale="tr" mode="individuals" />; }
