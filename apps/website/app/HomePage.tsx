import Link from "next/link";
import GovernanceEvidence from "./GovernanceEvidence";
import ProductExperience from "./ProductExperience";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "From goal to finished result",
    title: "Describe what you need. ILAIOS manages the work to a verified result.",
    lead: "Start with one clear outcome. ILAIOS coordinates the work, applies the controls that matter, checks the result and keeps the evidence with the delivery.",
    primary: "See what ILAIOS can create",
    secondary: "How it works",
    proof: [["One goal", "Start with the outcome, not a stack of tools."], ["Managed execution", "Work stays inside explicit permissions and controls."], ["Checked delivery", "Results are reviewed against the checks that apply before delivery."]],
    outcomesEyebrow: "What you can create",
    outcomesTitle: "One product. Different finished outcomes.",
    outcomesLead: "Choose the result you need. ILAIOS can combine research and production work without making you operate every underlying tool separately.",
    outcomes: [
      ["Website", "From a business goal to a responsive website with browser, accessibility and release checks.", "/factories/web"],
      ["Video", "From a brief and references to a finished media deliverable with render and quality checks.", "/factories/video"],
      ["Software", "From a bounded repository task to reviewed code, tests and change evidence.", "/factories/software"],
      ["Application", "From an application goal to build and test work inside explicit release boundaries.", "/factories/app"],
      ["Research", "From a question to source-grounded analysis with reviewable supporting evidence.", "/factories/research-data"],
    ],
    processEyebrow: "How it works",
    processTitle: "A simple path from request to finished work.",
    process: [["01", "Describe", "Tell ILAIOS the result you want."], ["02", "Execute", "ILAIOS coordinates the permitted work and dependencies."], ["03", "Verify", "Applicable checks evaluate the result."], ["04", "Deliver", "Accepted work is returned with reviewable evidence."]],
    controlEyebrow: "Built-in control",
    controlTitle: "Powerful execution should still have clear boundaries.",
    controlLead: "Identity, permissions, approvals and evidence remain part of the ILAIOS control model. Technical details live in Architecture and Documentation; the product experience stays outcome-first.",
    architecture: "Explore the architecture",
    closeEyebrow: "Start with the outcome",
    closeTitle: "What do you want ILAIOS to finish?",
    closePrimary: "Explore production outcomes",
  },
  tr: {
    eyebrow: "Hedeften bitmiş sonuca",
    title: "Ne istediğini anlat. ILAIOS işi yönetip doğrulanmış sonuca taşısın.",
    lead: "Tek bir sonuçla başla. ILAIOS gereken işi koordine eder, gerekli kontrolleri uygular, sonucu doğrular ve kanıtı teslimatla birlikte tutar.",
    primary: "ILAIOS neler üretebilir?",
    secondary: "Nasıl çalışır?",
    proof: [["Tek hedef", "Araçları değil, istediğin sonucu tarif et."], ["Yönetilen yürütme", "İş açık izinler ve kontroller içinde kalır."], ["Kontrollü teslim", "Sonuç, teslimden önce geçerli kontrollerle değerlendirilir."]],
    outcomesEyebrow: "Neler üretebilirsin?",
    outcomesTitle: "Tek ürün. Farklı bitmiş sonuçlar.",
    outcomesLead: "İhtiyacın olan sonucu seç. ILAIOS, her aracı ayrı ayrı işletmeni gerektirmeden araştırma ve üretim işlerini bir araya getirebilir.",
    outcomes: [
      ["Web sitesi", "Bir iş hedefinden responsive web sitesine; tarayıcı, erişilebilirlik ve yayın kontrolleriyle.", "/tr/factories/web"],
      ["Video", "Bir brief ve referanslardan bitmiş medya çıktısına; render ve kalite kontrolleriyle.", "/tr/factories/video"],
      ["Yazılım", "Sınırları belirli bir kod deposu görevinden incelenmiş kod, test ve değişiklik kanıtına.", "/tr/factories/software"],
      ["Uygulama", "Bir uygulama hedefinden açık derleme, test ve yayın sınırları içindeki çalışmaya.", "/tr/factories/app"],
      ["Araştırma", "Bir sorudan kaynak temelli analize ve incelenebilir destekleyici kanıta.", "/tr/factories/research-data"],
    ],
    processEyebrow: "Nasıl çalışır?",
    processTitle: "İstekten bitmiş işe uzanan sade bir yol.",
    process: [["01", "Tarif et", "İstediğin sonucu ILAIOS'a anlat."], ["02", "Yürüt", "ILAIOS izin verilen işi ve bağımlılıkları koordine eder."], ["03", "Doğrula", "Geçerli kontroller sonucu değerlendirir."], ["04", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."]],
    controlEyebrow: "Yerleşik kontrol",
    controlTitle: "Güçlü yürütmenin sınırları da açık olmalı.",
    controlLead: "Kimlik, izinler, onaylar ve kanıt ILAIOS kontrol modelinin parçası olarak kalır. Teknik ayrıntılar Mimari ve Dokümantasyon'da bulunur; ürün deneyimi sonuç odaklı kalır.",
    architecture: "Mimariyi incele",
    closeEyebrow: "Sonuçla başla",
    closeTitle: "ILAIOS'un neyi bitirmesini istiyorsun?",
    closePrimary: "Üretim sonuçlarını keşfet",
  },
} as const;

export default function HomePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="home-hero shell" data-visual-role="home-hero">
      <div className="home-hero-copy" data-visual-role="homepage-v2-authoritative"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.primary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link></div></div>
      <ProductExperience locale={locale} />
    </section>
    <div className="proof-strip"><div className="shell proof-strip-grid">{c.proof.map(([title, text]) => <div key={title}><strong>{title}</strong><span>{text}</span></div>)}</div></div>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.outcomesEyebrow}</div><h2>{c.outcomesTitle}</h2></div><p>{c.outcomesLead}</p></div><div className="outcome-showcase">{c.outcomes.map(([title,text,href], index) => <Link className="outcome-row" href={href} key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{title}</h3><p>{text}</p></div><strong aria-hidden="true">→</strong></Link>)}</div></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{c.processEyebrow}</div><h2>{c.processTitle}</h2></div></div><div className="process-rail">{c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell evidence-story"><div className="evidence-story-copy"><div className="eyebrow">{c.controlEyebrow}</div><h2>{c.controlTitle}</h2><p>{c.controlLead}</p><Link className="text-link" href={`${base}/architecture`}>{c.architecture} →</Link></div><GovernanceEvidence locale={locale} /></div></section>
    <div className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.closeEyebrow}</div><h2>{c.closeTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/factories`}>{c.closePrimary}</Link></div></div></div>
  </>;
}