import Link from "next/link";

type Locale = "en" | "tr";

type Factory = readonly [name: string, outcome: string, readiness: string, href: string];

const copy = {
  en: {
    eyebrow: "Nine production areas",
    title: "Different outcomes. One governed product.",
    lead: "ILAIOS has nine bounded production areas. Each focuses on a different kind of finished work while shared platform controls keep identity, permissions, approvals and evidence connected.",
    catalogTitle: "Choose the outcome you want to explore.",
    catalogLead: "Public readiness is shown conservatively. Preview means a bounded evidence-backed path exists; in-development areas are not presented as generally available production services.",
    open: "Explore",
    factories: [
      ["Web", "Websites and site revisions with browser, accessibility and release checks.", "Preview", "/factories/web"],
      ["Video / Media", "Reference-driven media work spanning script, assets, render and validation.", "Preview", "/factories/video"],
      ["Software", "Bounded repository engineering with reviewed code, tests and change evidence.", "Preview", "/factories/software"],
      ["Applications", "Application planning, bounded build, tests and release-readiness work.", "Preview", "/factories/app"],
      ["Research / Data", "Source-grounded research and structured analysis with reviewable provenance.", "In development", "/factories/research-data"],
      ["Security", "Authorized defensive assessment and remediation inside explicit scope.", "In development", "/factories/security"],
      ["Creative / Documents", "Controlled document composition, validation and reviewable export paths.", "In development", "/factories/creative-document"],
      ["Commerce / Growth", "Evidence-backed growth proposals and review-gated commercial work.", "In development", "/factories/commerce-growth"],
      ["Personal Operations", "Reviewable personal workflows whose consequential side effects remain separately governed.", "In development", "/factories/personal-operations"],
    ] as readonly Factory[],
    combineEyebrow: "Work can combine",
    combineTitle: "One goal can use more than one production area.",
    combineLead: "A launch may combine research, a website, software changes and media while the user stays focused on the finished result.",
    closePrimary: "See capabilities",
    closeSecondary: "How ILAIOS works",
  },
  tr: {
    eyebrow: "Dokuz üretim alanı",
    title: "Farklı sonuçlar. Tek yönetilen ürün.",
    lead: "ILAIOS'un dokuz sınırlandırılmış üretim alanı vardır. Her biri farklı bir bitmiş iş türüne odaklanırken kimlik, izinler, onaylar ve kanıt ortak platform kontrollerinde bağlı kalır.",
    catalogTitle: "Keşfetmek istediğin sonucu seç.",
    catalogLead: "Kullanıma hazırlık seviyesi temkinli biçimde gösterilir. Önizleme, sınırları belirli ve kanıtlı bir yol bulunduğunu; geliştiriliyor ise alanın genel kullanıma açık production hizmeti olarak sunulmadığını belirtir.",
    open: "İncele",
    factories: [
      ["Web", "Tarayıcı, erişilebilirlik ve yayın kontrolleriyle web sitesi ve site revizyonları.", "Önizleme", "/tr/factories/web"],
      ["Video / Medya", "Senaryo, varlıklar, render ve doğrulamayı kapsayan referans odaklı medya işi.", "Önizleme", "/tr/factories/video"],
      ["Yazılım", "İncelenmiş kod, testler ve değişiklik kanıtıyla sınırları belirli repository mühendisliği.", "Önizleme", "/tr/factories/software"],
      ["Uygulamalar", "Uygulama planlama, sınırlandırılmış build, test ve yayına hazırlık çalışması.", "Önizleme", "/tr/factories/app"],
      ["Araştırma / Veri", "İncelenebilir kaynak kökeniyle kaynak temelli araştırma ve yapılandırılmış analiz.", "Geliştiriliyor", "/tr/factories/research-data"],
      ["Güvenlik", "Açık yetki kapsamı içinde savunma odaklı değerlendirme ve düzeltme.", "Geliştiriliyor", "/tr/factories/security"],
      ["Yaratıcı / Dokümanlar", "Kontrollü doküman oluşturma, doğrulama ve incelenebilir dışa aktarma yolları.", "Geliştiriliyor", "/tr/factories/creative-document"],
      ["Ticaret / Büyüme", "Kanıta dayalı büyüme önerileri ve inceleme kapılı ticari çalışma.", "Geliştiriliyor", "/tr/factories/commerce-growth"],
      ["Kişisel Operasyon", "Önemli dış etkileri ayrıca yönetilen, incelenebilir kişisel iş akışları.", "Geliştiriliyor", "/tr/factories/personal-operations"],
    ] as readonly Factory[],
    combineEyebrow: "Birlikte çalışabilir",
    combineTitle: "Tek hedef birden fazla üretim alanını kullanabilir.",
    combineLead: "Bir lansman araştırma, web sitesi, yazılım değişiklikleri ve medyayı birleştirebilir; kullanıcı ise bitmiş sonuca odaklanır.",
    closePrimary: "Yetenekleri gör",
    closeSecondary: "ILAIOS nasıl çalışır?",
  },
} as const;

export default function FactoriesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.eyebrow}</div><h2>{c.catalogTitle}</h2></div><p>{c.catalogLead}</p></div><div className="grid three-up">{c.factories.map(([name, outcome, readiness, href], index) => <article className="card" key={href}><span className="micro-label">{String(index + 1).padStart(2, "0")} · {readiness}</span><h3>{name}</h3><p>{outcome}</p><Link className="text-link" href={href}>{c.open} →</Link></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.combineEyebrow}</div><h2>{c.combineTitle}</h2><p>{c.combineLead}</p></div><div className="actions"><Link className="button" href={`${base}/capabilities`}>{c.closePrimary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.closeSecondary}</Link></div></div></section>
  </>;
}
