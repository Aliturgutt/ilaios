import type { Metadata } from "next";
import ProductDeepDive from "../../ProductDeepDive";
export const metadata: Metadata = { title: "ILAIOS Core", description: "ILAIOS Core'un yetki, doğrulama, kanıt ve recovery modelini inceleyin.", alternates: { canonical: "/tr/core", languages: { tr: "/tr/core", en: "/core", "x-default": "/core" } } };
export default function Page(){ return <ProductDeepDive locale="tr" mode="core" />; }
