import Link from "next/link";
import FactoryExplorer from "./FactoryExplorer";
import ThemedDiagram from "./ThemedDiagram";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Production outcomes",
    title: "Create different kinds of finished work from one goal.",
    lead: "Websites, video, software, applications and research are different outcomes, but you should not have to operate them as separate AI products.",
    visualEyebrow: "One goal, the right production path",
    visualTitle: "ILAIOS coordinates the work needed for the outcome.",
    visualLead: "A request can use one or more production areas while the user stays focused on the result rather than provider, model or tool configuration.",
    visualCaption: "Illustrative production map showing one goal resolving across specialized outcome paths.",
    combineEyebrow: "Combined outcomes",
    combineTitle: "A single launch can require more than one kind of work.",
    combineLead: "For example, a product launch may require research, a website, software changes and media. ILAIOS is designed to coordinate the relevant work under the same control model.",
    combine: [["Research", "Understand the market and source material."], ["Website", "Create the customer-facing product surface."], ["Software / App", "Implement the bounded product work that is needed."], ["Video", "Create supporting media from approved material."], ["Verify", "Apply the checks that belong to each deliverable."]],
    sharedEyebrow: "Shared project context",
    sharedTitle: "Production areas can use the same authorized project knowledge.",
    sharedLead: "That keeps context consistent across deliverables without turning project knowledge into another product surface or a separate authority.",
    closeTitle: "Choose the outcome you want to explore.",
    closePrimary: "See all capabilities",
    closeSecondary: "How ILAIOS works",
  },
  tr: {
    eyebrow: "Üretim sonuçları",
    title: "Tek bir hedeften farklı türde bitmiş işler üret.",
    lead: "Web sitesi, video, yazılım, uygulama ve araştırma farklı sonuçlardır; ancak bunları ayrı ayrı yapay zekâ ürünleri gibi işletmek zorunda olmamalısın.",
    visualEyebrow: "Tek hedef, doğru üretim yolu",
    visualTitle: "ILAIOS sonuç için gereken işi koordine eder.",
    visualLead: "Bir istek bir veya birden fazla üretim alanını kullanabilir; kullanıcı sağlayıcı, model veya araç ayarı yerine sonuca odaklanır.",
    visualCaption: "Tek bir hedefin uzmanlaşmış sonuç yollarına ayrılmasını gösteren açıklayıcı üretim haritası.",
    combineEyebrow: "Birleşik sonuçlar",
    combineTitle: "Tek bir lansman birden fazla iş türü gerektirebilir.",
    combineLead: "Örneğin bir ürün lansmanı araştırma, web sitesi, yazılım değişiklikleri ve medya gerektirebilir. ILAIOS ilgili işi aynı kontrol modeli altında koordine etmek üzere tasarlanmıştır.",
    combine: [["Araştırma", "Pazarı ve kaynak materyali anla."], ["Web sitesi", "Müşteriye açık ürün yüzeyini oluştur."], ["Yazılım / Uygulama", "Gereken sınırları belirli ürün işini uygula."], ["Video", "Onaylı materyalden destekleyici medya üret."], ["Doğrula", "Her teslimata ait kontrolleri uygula."]],
    sharedEyebrow: "Paylaşılan proje bağlamı",
    sharedTitle: "Üretim alanları aynı yetkili proje bilgisinden yararlanabilir.",
    sharedLead: "Bu, proje bilgisini ayrı bir ürün yüzeyine veya ikinci bir otoriteye dönüştürmeden teslimatlar arasındaki bağlamı tutarlı tutar.",
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
    <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.visualEyebrow}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div><ThemedDiagram light="/visuals/factory-orchestration-light.avif" dark="/visuals/factory-orchestration-dark.avif" alt={locale === "tr" ? "Tek bir hedefin web, uygulama, yazılım, video ve araştırma üretim yollarına yönlenmesini gösteren ILAIOS üretim haritası" : "ILAIOS production map showing one goal resolving to web, app, software, video and research outcome paths"} caption={c.visualCaption} priority /></div></section>
    <section className="section"><div className="shell"><FactoryExplorer locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.combineEyebrow}</div><h2>{c.combineTitle}</h2></div><p>{c.combineLead}</p></div><div className="runtime-line">{c.combine.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section"><div className="shell architecture-story"><div className="architecture-story-copy"><div className="eyebrow">{c.sharedEyebrow}</div><h2>{c.sharedTitle}</h2><p>{c.sharedLead}</p></div></div></section>
    <section className="section compact-section surface-section"><div className="shell compact-cta"><div><h2>{c.closeTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/capabilities`}>{c.closePrimary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.closeSecondary}</Link></div></div></section>
  </>;
}
