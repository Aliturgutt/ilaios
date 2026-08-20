import type { Metadata } from "next";
import HomePage from "../HomePage";
import SuppliedVisual from "../SuppliedVisual";

export const metadata: Metadata = { title: "Yönetilen Yapay Zekâ İşletim Sistemi", description: "ILAIOS, kimliği doğrulanmış hedefleri kanıtla desteklenen yönetilen ve doğrulanmış bitmiş ürün iş akışlarına taşır.", alternates: { canonical: "/tr", languages: { tr: "/tr", en: "/", "x-default": "/" } } };

export default function Page() { return <><HomePage locale="tr" /><section className="section surface-section"><div className="shell"><SuppliedVisual priority light="/website-v2/homepage-light.avif" dark="/website-v2/homepage-dark.avif" alt="ILAIOS yönetilen dijital çalışma platformunda iş hedefinin tek yönetilen Core, paylaşılan yetenekler, üretim factory'leri ve doğrulama üzerinden kanıta dayalı sonuca ilerleyişi." caption="Kanonik yön: iş akışları ikinci bir yürütme yetkisi oluşturmadan paylaşılan yönetilen yetenekleri ve uzmanlaşmış üretim factory'lerini birleştirir." /></div></section></>; }
