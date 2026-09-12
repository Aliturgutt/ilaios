import Link from "next/link";
import CanonicalSystemDetail from "./CanonicalSystemDetail";
import FactoryExplorer from "./FactoryExplorer";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Nine production areas",
    title: "Create different kinds of finished work from one governed product.",
    lead: "ILAIOS has nine bounded production areas: Web, Video / Media, Software, App, Research / Data, Security, Creative / Document, Commerce / Growth and Personal Operations.",
    overviewTitle: "See all nine production areas at a glance.",
    overviewLead: "Each area owns a different kind of outcome, while identity, policy, approvals, routing, evidence and state remain shared platform controls.",
    overview: [["Web", "/factories/web"], ["Video / Media", "/factories/video"], ["Software", "/factories/software"], ["App", "/factories/app"], ["Research / Data", "/factories/research-data"], ["Security", "/factories/security"], ["Creative / Document", "/factories/creative-document"], ["Commerce / Growth", "/factories/commerce-growth"], ["Personal Operations", "/factories/personal-operations"]],
    visualEyebrow: "One goal, the right production path",
    visualTitle: "ILAIOS coordinates the work needed for the outcome.",
    visualLead: "A request can use one or more production areas while the user stays focused on the result rather than provider, model or tool configuration.",
    combineEyebrow: "Cross-factory composition",
    combineTitle: "A single launch can require more than one kind of work.",
    combineLead: "For example, a product launch may require research, a website, software changes and media. ILAIOS is designed to coordinate the relevant work under the same control model.",
    combine: [["Research", "Understand the market and source material."], ["Website", "Create the customer-facing product surface."], ["Software / App", "Implement the bounded product work that is needed."], ["Video", "Create supporting media from approved material."], ["Verify", "Apply the checks that belong to each deliverable."]],
    sharedEyebrow: "Shared project context",
    sharedTitle: "Production areas can use the same authorized project knowledge.",
    sharedLead: "That keeps context consistent across deliverables without turning project knowledge into another product surface or a separate authority.",
    assuranceTitle: "Shared knowledge remains governed context, not another production authority.",
    assuranceLead: "The technical assurance view below keeps authorization and provenance boundaries explicit without putting infrastructure jargon in the primary marketing flow.",
    closeTitle: "Choose the outcome you want to explore.",
    closePrimary: "See all capabilities",
    closeSecondary: "How ILAIOS works",
  },
  tr: {
    eyebrow: "Dokuz üretim alanı",
    title: "Tek yönetilen üründen farklı türde bitmiş işler üret.",
    lead: "ILAIOS'un dokuz sınırlandırılmış üretim alanı vardır: Web, Video / Medya, Yazılım, Uygulama, Araştırma / Veri, Güvenlik, Creative / Doküman, Commerce / Büyüme ve Kişisel Operasyon.",
    overviewTitle: "Dokuz üretim alanının tamamını tek bakışta gör.",
    overviewLead: "Her alan farklı bir sonuç türüne odaklanır; kimlik, politika, onay, routing, kanıt ve durum ortak platform kontrolleri olarak kalır.",
    overview: [["Web", "/tr/factories/web"], ["Video / Medya", "/tr/factories/video"], ["Yazılım", "/tr/factories/software"], ["Uygulama", "/tr/factories/app"], ["Araştırma / Veri", "/tr/factories/research-data"], ["Güvenlik", "/tr/factories/security"], ["Creative / Doküman", "/tr/factories/creative-document"], ["Commerce / Büyüme", "/tr/factories/commerce-growth"], ["Kişisel Operasyon", "/tr/factories/personal-operations"]],
    visualEyebrow: "Tek hedef, doğru üretim yolu",
    visualTitle: "ILAIOS sonuç için gereken işi koordine eder.",
    visualLead: "Bir istek bir veya birden fazla üretim alanını kullanabilir; kullanıcı sağlayıcı, model veya araç ayarı yerine sonuca odaklanır.",
    combineEyebrow: "Üretim alanları arası bileşim",
    combineTitle: "Tek bir lansman birden fazla iş türü gerektirebilir.",
    combineLead: "Örneğin bir ürün lansmanı araştırma, web sitesi, yazılım değişiklikleri ve medya gerektirebilir. ILAIOS ilgili işi aynı kontrol modeli altında koordine etmek üzere tasarlanmıştır.",
    combine: [["Araştırma", "Pazarı ve kaynak materyali anla."], ["Web sitesi", "Müşteriye açık ürün yüzeyini oluştur."], ["Yazılım / Uygulama", "Gereken sınırları belirli ürün işini uygula."], ["Video", "Onaylı materyalden destekleyici medya üret."], ["Doğrula", "Her teslimata ait kontrolleri uygula."]],
    sharedEyebrow: "Paylaşılan proje bağlamı",
    sharedTitle: "Üretim alanları aynı yetkili proje bilgisinden yararlanabilir.",
    sharedLead: "Bu, proje bilgisini ayrı bir ürün yüzeyine veya ikinci bir otoriteye dönüştürmeden teslimatlar arasındaki bağlamı tutarlı tutar.",
    assuranceTitle: "Paylaşılan bilgi, yeni bir üretim yetkisi değil yönetilen bağlam olarak kalır.",
    assuranceLead: "Aşağıdaki teknik güvence görünümü, ana pazarlama akışını altyapı jargonuyla doldurmadan yetki ve kaynak kökeni sınırlarını açık tutar.",
    closeTitle: "Keşfetmek istediğin sonucu seç.",
    closePrimary: "Tüm yetenekleri gör",
    closeSecondary: "ILAIOS nasıl çalışır?",
  },
} as const;

export default function FactoriesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell capability-factory-band"><div><div className="eyebrow">{c.eyebrow}</div><h2>{c.overviewTitle}</h2><p>{c.overviewLead}</p></div><div className="factory-link-cloud">{c.overview.map(([label, href], index) => <Link key={href} href={href}><span>{String(index + 1).padStart(2, "0")}</span>{label}</Link>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.visualEyebrow}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div><FactoryExplorer locale={locale} /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.combineEyebrow}</div><h2>{c.combineTitle}</h2></div><p>{c.combineLead}</p></div><div className="runtime-line">{c.combine.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section factory-shared-context" style={{ paddingTop: "32px", paddingBottom: "32px" }}><div className="shell"><div className="architecture-story-copy" style={{ maxWidth: "760px" }}><div className="eyebrow">{c.sharedEyebrow}</div><h2>{c.sharedTitle}</h2><p>{c.sharedLead}</p></div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><h2>{c.assuranceTitle}</h2></div><p>{c.assuranceLead}</p></div><CanonicalSystemDetail locale={locale} variant="knowledge" /></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><h2>{c.closeTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/capabilities`}>{c.closePrimary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.closeSecondary}</Link></div></div></section>
  </>;
}
