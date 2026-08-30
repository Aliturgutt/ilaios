import type { Metadata } from "next";
import CapabilitiesPage from "../../CapabilitiesPage";
export const metadata: Metadata = { title: "Yetenekler", description: "Kanonik ILAIOS platform yeteneklerini bitmiş ürün üreten alanlardan ayrı olarak inceleyin.", alternates: { canonical: "/tr/capabilities", languages: { tr: "/tr/capabilities", en: "/capabilities", "x-default": "/capabilities" } } };
export default function Page() { return <CapabilitiesPage locale="tr" />; }
