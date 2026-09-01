import type { Metadata } from "next";
import AudiencePage from "../../AudiencePage";
export const metadata: Metadata = { title: "Kurumlar İçin", description: "ILAIOS'un kurumlarda otomasyon ve native finished-product workflow'larını açık yetki, doğrulama ve kanıt modeliyle nasıl yönettiğini inceleyin.", alternates: { canonical: "/tr/enterprise", languages: { tr: "/tr/enterprise", en: "/enterprise", "x-default": "/enterprise" } } };
export default function Page(){ return <AudiencePage locale="tr" audience="enterprise" />; }
