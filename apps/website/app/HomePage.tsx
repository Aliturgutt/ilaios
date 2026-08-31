import Link from "next/link";
import FactoryExplorer from "./FactoryExplorer";
import GovernanceEvidence from "./GovernanceEvidence";
import ProductExperience from "./ProductExperience";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Governed Digital Operating Platform",
    title: "Turn business goals into coordinated, evidence-backed outcomes.",
    lead: "ILAIOS brings research, intelligence, operations and digital production under one governed execution model. A goal can resolve across shared capabilities and specialized factories without moving authority into models or providers.",
    primary: "See what you can create",
    secondary: "How it works",
    proof: [["One governed authority", "Policy, approvals and evidence stay shared."], ["Business + production", "Intelligence and operations can compose specialized factories."], ["Evidence built in", "Acceptance is verified, not narrated."]],
    operatingEyebrow: "Enterprise operating layer",
    operatingTitle: "More than digital production: a governed layer for coordinated business work.",
    operatingLead: "This is the product direction, not a second Core or a claim that every business workflow is production-ready today. Business functions compose the same governed capabilities and production factories.",
    operating: [["Executive intelligence", "Strategy, KPI, performance and risk analysis with evidence-backed recommendations."], ["Operations", "Task and process coordination, execution monitoring, exception handling and approval-gated actions."], ["Finance & cost intelligence", "Cost visibility, budget awareness, resource efficiency and FinOps-informed decisions — not autonomous banking or accounting."], ["Growth & marketing", "Market intelligence, campaign planning, content workflows and measurement-oriented growth work."], ["Commerce & sales", "Proposal, offer and revenue-operation workflows with controlled integrations and approval-gated external actions."], ["Research & data", "Source-grounded research, competitive intelligence and provenance-aware analysis."]],
    operatingNote: "Canonical direction · In development",
    processEyebrow: "Execution protocol",
    processTitle: "A simple request at the surface. Explicit control underneath.",
    process: [["01", "Goal", "Authenticated intent enters the system."], ["02", "Plan", "Context, policy and dependencies define the path."], ["03", "Execute", "Bounded capabilities perform admitted work."], ["04", "Validate", "Tests and acceptance criteria evaluate the result."], ["05", "Deliver", "Accepted work is surfaced with reviewable evidence."]],
    goalEyebrow: "Cross-functional outcome",
    goalTitle: "One business goal can coordinate multiple capabilities and factories.",
    goalLead: "A user should not have to operate each factory as a separate product. The target model resolves the goal into the work that is needed while one governance and evidence spine remains authoritative.",
    goalFlow: ["Business goal", "Research", "Market intelligence", "Strategy", "Budget / risk", "Web + Software / App", "Video / content", "Growth + commerce", "Measurement", "Evidence"],
    visualEyebrow: "How the system works",
    visualTitle: "The operating model is visible as a governed system, not hidden inside model output.",
    visualLead: "These product explanations keep authority, bounded factories, replaceable execution resources and evidence-linked acceptance visible without making users operate the internal provider stack.",
    archEyebrow: "Public system language",
    archTitle: "Business workflows sit above — never beside — the canonical execution authority.",
    archText: "The Enterprise Operating Layer is a product and workflow composition layer, not a second orchestrator, router, Policy Engine or runtime. Goal → bounded planning → governed execution → validation → evidence → accepted result remains the authoritative spine.",
    evidenceEyebrow: "Why governance matters",
    evidenceTitle: "Generated is not the same as finished.",
    ctaEyebrow: "Provider independent",
    ctaTitle: "Models, tools and providers can change. The ILAIOS product boundary does not.",
    architecture: "Architecture",
    factories: "All factories",
  },
  tr: {
    eyebrow: "Yönetilen Dijital Çalışma Platformu",
    title: "İş hedeflerini koordineli ve kanıta dayalı sonuçlara dönüştürün.",
    lead: "ILAIOS; araştırma, kurumsal zekâ, operasyon ve dijital üretimi tek yönetilen yürütme modeli altında birleştirir. Bir hedef, yetkiyi modellere veya sağlayıcılara taşımadan paylaşılan yeteneklere ve uzmanlaşmış üretim alanlarına çözümlenebilir.",
    primary: "Neler oluşturabileceğini gör",
    secondary: "Nasıl çalışır?",
    proof: [["Tek yönetilen yetki", "Politika, onay ve kanıt paylaşılır."], ["İş + üretim", "Zekâ ve operasyon uzmanlaşmış üretim alanlarını birleştirebilir."], ["Kanıt işin parçası", "Kabul anlatılmaz; doğrulanır."]],
    operatingEyebrow: "Kurumsal çalışma katmanı",
    operatingTitle: "Dijital üretimin ötesinde: koordineli iş süreçleri için yönetilen bir çalışma katmanı.",
    operatingLead: "Bu bir ürün yönüdür; ikinci bir Core değildir ve tüm iş akışlarının bugün production-ready olduğu iddiasını taşımaz. İş fonksiyonları aynı yönetilen yetenekleri ve üretim alanlarını bir araya getirir.",
    operating: [["Yönetici zekâsı", "Strateji, KPI, performans ve risk analizi ile kanıta dayalı öneriler."], ["Operasyonlar", "Görev ve süreç koordinasyonu, yürütme izleme, istisna yönetimi ve onay kapılı işlemler."], ["Finans ve maliyet zekâsı", "Maliyet görünürlüğü, bütçe farkındalığı, kaynak verimliliği ve FinOps odaklı kararlar — otonom bankacılık veya muhasebe değil."], ["Büyüme ve pazarlama", "Pazar zekâsı, kampanya planlama, içerik akışları ve ölçüm odaklı büyüme çalışmaları."], ["Ticaret ve satış", "Kontrollü entegrasyonlar ve onay kapılı dış işlemlerle teklif, öneri ve gelir operasyonu akışları."], ["Araştırma ve veri", "Kaynak temelli araştırma, rekabet zekâsı ve provenance-aware analiz."]],
    operatingNote: "Kanonik yön · Geliştiriliyor",
    processEyebrow: "Yürütme protokolü",
    processTitle: "Yüzeyde basit istek. Altında açık kontrol.",
    process: [["01", "Hedef", "Kimliği doğrulanmış niyet sisteme girer."], ["02", "Plan", "Bağlam, politika ve bağımlılıklar yolu belirler."], ["03", "Yürüt", "Sınırlandırılmış yetenekler kabul edilen işi yapar."], ["04", "Doğrula", "Testler ve kabul ölçütleri sonucu değerlendirir."], ["05", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."]],
    goalEyebrow: "Fonksiyonlar arası sonuç",
    goalTitle: "Tek bir iş hedefi birden fazla yetenek ve üretim alanını koordine edebilir.",
    goalLead: "Kullanıcı her üretim alanını ayrı bir ürün gibi işletmek zorunda kalmamalı. Hedef model, ihtiyacı gereken işlere çözümlerken tek yönetişim ve kanıt omurgası yetkili kalır.",
    goalFlow: ["İş hedefi", "Araştırma", "Pazar zekâsı", "Strateji", "Bütçe / risk", "Web + Yazılım / Uygulama", "Video / içerik", "Büyüme + ticaret", "Ölçüm", "Kanıt"],
    visualEyebrow: "Sistem nasıl çalışır?",
    visualTitle: "Çalışma modeli, model çıktısının içinde saklanmak yerine yönetilen bir sistem olarak görünür.",
    visualLead: "Bu ürün anlatımları yetkiyi, sınırlandırılmış factory'leri, değiştirilebilir yürütme kaynaklarını ve kanıta bağlı kabulü görünür tutar; kullanıcıya dahili provider stack'ini işlettirmez.",
    archEyebrow: "Public sistem dili",
    archTitle: "İş akışları kanonik yürütme yetkisinin üzerinde yer alır; yanında ikinci bir otorite oluşturmaz.",
    archText: "Kurumsal Çalışma Katmanı bir ürün ve workflow composition katmanıdır; ikinci orchestrator, router, Policy Engine veya runtime değildir. Hedef → sınırlandırılmış planlama → yönetilen yürütme → doğrulama → kanıt → kabul edilmiş sonuç yetkili omurga olarak kalır.",
    evidenceEyebrow: "Yönetim neden önemli?",
    evidenceTitle: "Üretilmiş olmak, bitmiş olmak değildir.",
    ctaEyebrow: "Sağlayıcı bağımsızlığı",
    ctaTitle: "Modeller, araçlar ve sağlayıcılar değişebilir. ILAIOS ürün sınırı değişmez.",
    architecture: "Mimari",
    factories: "Tüm üretim alanları",
  },
} as const;

export default function HomePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="homepage-v2 home-hero shell" data-visual-role="home-hero"><div className="home-hero-copy" data-visual-role="homepage-v2-authoritative" data-capabilities-href={`${base}/capabilities`}><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.primary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link></div></div><ProductExperience locale={locale} /></section>
    <div className="proof-strip"><div className="shell proof-strip-grid">{c.proof.map(([title, text]) => <div key={title}><strong>{title}</strong><span>{text}</span></div>)}</div></div>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.operatingEyebrow}</div><h2>{c.operatingTitle}</h2></div><p>{c.operatingLead}</p></div><div className="grid two-up">{c.operating.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><p className="muted">{c.operatingNote}</p></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{c.processEyebrow}</div><h2>{c.processTitle}</h2></div></div><div className="process-rail home-process-rail-v2" data-visual-role="five-step-execution">{c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><FactoryExplorer locale={locale} /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.goalEyebrow}</div><h2>{c.goalTitle}</h2></div><p>{c.goalLead}</p></div><div className="runtime-line home-output-index-v2">{c.goalFlow.map((step,index) => <div key={step}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step}</strong></div>)}</div><p className="muted">{c.operatingNote}</p></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.visualEyebrow}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div><SystemVisuals locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell architecture-story"><div className="architecture-story-copy"><div className="eyebrow">{c.archEyebrow}</div><h2>{c.archTitle}</h2><p>{c.archText}</p><Link className="text-link" href={`${base}/architecture`}>{c.architecture} →</Link></div><SpatialArchitecture locale={locale} compact /></div></section>
    <section className="section evidence-section home-control-ledger-v2"><div className="shell evidence-story evidence-story-interactive"><div className="evidence-story-copy"><div className="eyebrow">{c.evidenceEyebrow}</div><h2>{c.evidenceTitle}</h2></div><GovernanceEvidence locale={locale} /></div></section>
    <div className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.ctaEyebrow}</div><h2>{c.ctaTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/architecture`}>{c.architecture}</Link><Link className="button secondary" href={`${base}/factories`}>{c.factories}</Link></div></div></div>
  </>;
}