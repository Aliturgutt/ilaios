import type { Metadata } from "next";
import FactoriesPage from "../../FactoriesPage";
export const metadata: Metadata = { title: "ILAIOS Üretim Alanları", description: "Tek bir yönetim modeli altında uzmanlaşmış ILAIOS üretim ve operasyon alanlarını inceleyin.", alternates: { canonical: "/tr/factories", languages: { tr: "/tr/factories", en: "/factories", "x-default": "/factories" } } };
export default function Page() { return <FactoriesPage locale="tr" />; }
