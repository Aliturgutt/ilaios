import Link from "next/link";
import FactoryExplorer from "./FactoryExplorer";
import GovernanceEvidence from "./GovernanceEvidence";
import ProductExperience from "./ProductExperience";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Governed AI Operating System",
    title: "Describe the outcome. ILAIOS governs the work to get there.",
    lead: "One authenticated goal can move through planning, bounded execution, validation and evidence toward a finished digital product.",
    primary: "See what you can create",
    secondary: "How it works",
    proof: [["One product brain", "Authority stays in the platform."], ["Native factories", "Web, video, software, app and more."], ["Evidence built in", "Acceptance is verified, not narrated."]],
    processEyebrow: "Execution protocol",
    processTitle: "A simple request at the surface. Explicit control underneath.",
    process: [["01", "Goal", "Authenticated intent enters the system."], ["02", "Plan", "Context, policy and dependencies define the path."], ["03", "Execute", "Bounded capabilities perform admitted work."], ["04", "Validate", "Tests and acceptance criteria evaluate the result."], ["05", "Deliver", "Accepted work is surfaced with reviewable evidence."]],
    visualEyebrow: "How the system works",
    visualTitle: "The operating model is visible as a governed system, not hidden inside model output.",
    visualLead: "These product explanations keep authority, bounded factories, replaceable execution resources and evidence-linked acceptance visible without making users operate the internal provider stack.",
    archEyebrow: "Public system language",
    archTitle: "Governed execution stays visible from goal to accepted result.",
    archText: "Goal → bounded planning → governed execution → validation → evidence → accepted result is the public product spine. Internal provider routing remains behind that boundary.",
    evidenceEyebrow: "Why governance matters",
    evidenceTitle: "Generated is not the same as finished.",
    ctaEyebrow: "Provider independent",
    ctaTitle: "Models, tools and providers can change. The ILAIOS product boundary does not.",
    architecture: "Architecture",
    factories: "All factories",
  },
  tr: {
    eyebrow: "Yönetilen Yapay Zekâ İşletim Sistemi",
    title: "Sonucu tarif edin. Oraya giden işi ILAIOS yönetsin.",
    lead: "Kimliği doğrulanmış tek bir hedef; planlama, sınırlandırılmış yürütme, doğrulama ve kanıt üzerinden bitmiş dijital ürüne ilerler.",
    primary: "Neler oluşturabileceğini gör",
    secondary: "Nasıl çalışır?",
    proof: [["Tek ürün beyni", "Yetki platformda kalır."], ["Yerleşik üretim alanları", "Web, video, yazılım, uygulama ve daha fazlası."], ["Kanıt işin parçası", "Kabul anlatılmaz; doğrulanır."]],
    processEyebrow: "Yürütme protokolü",
    processTitle: "Yüzeyde basit istek. Altında açık kontrol.",
    process: [["01", "Hedef", "Kimliği doğrulanmış niyet sisteme girer."], ["02", "Plan", "Bağlam, politika ve bağımlılıklar yolu belirler."], ["03", "Yürüt", "Sınırlandırılmış yetenekler kabul edilen işi yapar."], ["04", "Doğrula", "Testler ve kabul ölçütleri sonucu değerlendirir."], ["05", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."]],
    visualEyebrow: "Sistem nasıl çalışır?",
    visualTitle: "Çalışma modeli, model çıktısının içinde saklanmak yerine yönetilen bir sistem olarak görünür.",
    visualLead: "Bu ürün anlatımları yetkiyi, sınırlandırılmış factory'leri, değiştirilebilir yürütme kaynaklarını ve kanıta bağlı kabulü görünür tutar; kullanıcıya dahili provider stack'ini işlettirmez.",
    archEyebrow: "Public sistem dili",
    archTitle: "Yönetilen yürütme hedeften kabul edilmiş sonuca kadar görünür kalır.",
    archText: "Hedef → sınırlandırılmış planlama → yönetilen yürütme → doğrulama → kanıt → kabul edilmiş sonuç public ürün omurgasıdır. Dahili provider routing bu sınırın arkasında kalır.",
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
    <section className="home-hero shell" data-visual-role="home-hero">
      <div className="home-hero-copy">
        <div className="eyebrow">{c.eyebrow}</div>
        <h1>{c.title}</h1>
        <p className="lead">{c.lead}</p>
        <div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.primary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link></div>
      </div>
      <ProductExperience locale={locale} />
    </section>

    <section className="proof-strip"><div className="shell proof-strip-grid">{c.proof.map(([title, text]) => <div key={title}><strong>{title}</strong><span>{text}</span></div>)}</div></section>

    <section className="section"><div className="shell">
      <div className="compact-heading-row"><div><div className="eyebrow">{c.processEyebrow}</div><h2>{c.processTitle}</h2></div></div>
      <div className="process-rail" data-visual-role="five-step-execution">{c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div>
    </div></section>

    <section className="section surface-section"><div className="shell"><FactoryExplorer locale={locale} /></div></section>

    <section className="section"><div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{c.visualEyebrow}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div>
      <SystemVisuals locale={locale} />
    </div></section>

    <section className="section surface-section"><div className="shell architecture-story">
      <div className="architecture-story-copy"><div className="eyebrow">{c.archEyebrow}</div><h2>{c.archTitle}</h2><p>{c.archText}</p><Link className="text-link" href={`${base}/architecture`}>{c.architecture} →</Link></div>
      <SpatialArchitecture locale={locale} compact />
    </div></section>

    <section className="section evidence-section"><div className="shell evidence-story evidence-story-interactive">
      <div className="evidence-story-copy"><div className="eyebrow">{c.evidenceEyebrow}</div><h2>{c.evidenceTitle}</h2></div>
      <GovernanceEvidence locale={locale} />
    </div></section>

    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.ctaEyebrow}</div><h2>{c.ctaTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/architecture`}>{c.architecture}</Link><Link className="button secondary" href={`${base}/factories`}>{c.factories}</Link></div></div></section>
  </>;
}
