import type { Metadata } from "next";
import HomePage from "../HomePage";

export const metadata: Metadata = { title: "Yönetilen Yapay Zekâ İşletim Sistemi", description: "ILAIOS, kimliği doğrulanmış hedefleri kanıtla desteklenen yönetilen ve doğrulanmış bitmiş ürün iş akışlarına taşır.", alternates: { canonical: "/tr", languages: { tr: "/tr", en: "/", "x-default": "/" } } };

export default function Page() { return <HomePage locale="tr" />; }
