import Link from "next/link";
import FactoryExplorer from "./FactoryExplorer";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "ILAIOS Factories",
    title: "Specialized production paths under one governance model.",
    lead: "Factories turn different kinds of work into bounded, inspectable workflows instead of one generic generation surface.",
    note: "A factory name does not imply every target capability is deployed or generally available. Detail pages keep current foundations separate from canonical direction.",
    core: "One Core governs identity, policy, routing, validation, evidence and recovery across the factory layer.",
    coreCta: "Explore Core",
    capCta: "Capability map",
  },
  tr: {
    eyebrow: "ILAIOS Üretim Alanları",
    title: "Tek yönetim modeli altında uzmanlaşmış üretim yolları.",
    lead: "Her üretim alanı, farklı işleri tek bir genel üretim ekranına sıkıştırmak yerine sınırlandırılmış ve incelenebilir bir iş akışına dönüştürür.",
    note: "Bir üretim alanının adı, hedeflenen her yeteneğin bugün yayında veya genel kullanıma açık olduğu anlamına gelmez. Ayrıntı sayfaları güncel temeli kanonik yönden ayrı tutar.",
    core: "Kimlik, politika, yönlendirme, doğrulama, kanıt ve kurtarma tüm üretim alanlarında aynı Core tarafından yönetilir.",
    coreCta: "Core'u incele",
    capCta: "Yetenek haritası",
  },
} as const;

export default function FactoriesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell"><FactoryExplorer locale={locale} /></div></section>
    <section className="section compact-section"><div className="shell factory-truth-note"><span>{locale === "tr" ? "Ürün gerçeği" : "Product truth"}</span><p>{c.note}</p></div></section>
    <section className="section compact-section surface-section"><div className="shell compact-cta"><div><div className="eyebrow">ILAIOS Core</div><h2>{c.core}</h2></div><div className="actions"><Link className="button" href={`${base}/core`}>{c.coreCta}</Link><Link className="button secondary" href={`${base}/capabilities`}>{c.capCta}</Link></div></div></section>
  </>;
}
