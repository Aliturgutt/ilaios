import type { Metadata } from "next";
import SecurityPage from "../../SecurityPage";
export const metadata: Metadata = { title: "Güvenlik", description: "ILAIOS en az yetki, onay, doğrulama ve kanıt güvenlik modelini inceleyin.", alternates: { canonical: "/tr/security", languages: { tr: "/tr/security", en: "/security", "x-default": "/security" } } };
export default function Page() { return <SecurityPage locale="tr" />; }
