import type { Metadata } from "next";
import WebsiteV2HomeRecovery from "../WebsiteV2HomeRecovery";

export const metadata: Metadata = { title: "Yönetilen Yapay Zekâ İşletim Sistemi", description: "ILAIOS, kimliği doğrulanmış hedefleri kanıtla desteklenen yönetilen ve doğrulanmış bitmiş ürün iş akışlarına taşır.", alternates: { canonical: "/tr", languages: { tr: "/tr", en: "/", "x-default": "/" } } };

export default function Page() { return <WebsiteV2HomeRecovery locale="tr" />; }
