import type { Metadata } from "next";
import ArchitecturePage from "../../ArchitecturePage";
export const metadata: Metadata = { title: "Mimari", description: "ILAIOS kontrol katmanı mimarisini, yetki akışını, yönlendirmeyi, doğrulamayı ve kanıt yolunu inceleyin.", alternates: { canonical: "/tr/architecture", languages: { tr: "/tr/architecture", en: "/architecture", "x-default": "/architecture" } } };
export default function Page() { return <ArchitecturePage locale="tr" />; }
