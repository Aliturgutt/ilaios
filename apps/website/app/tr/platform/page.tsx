import type { Metadata } from "next";
import PlatformPage from "../../PlatformPage";
export const metadata: Metadata = { title: "Platform", description: "ILAIOS kontrol odaklı platformunun yetki, sınırlandırılmış yürütme, doğrulama ve kanıt modelini inceleyin.", alternates: { canonical: "/tr/platform", languages: { tr: "/tr/platform", en: "/platform", "x-default": "/platform" } } };
export default function Page() { return <PlatformPage locale="tr" />; }
