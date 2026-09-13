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
    outcomesEyebrow: "Nine production areas",
    outcomesTitle: "One product. Nine governed production areas.",
    outcomesLead: "Choose the result you need. ILAIOS can coordinate work across nine bounded production areas without making you operate every underlying tool separately.",
    outcomes: [
      ["Web", "Websites and site revisions moving through structure, implementation, browser, accessibility and release checks.", "/factories/web"],
      ["Video / Media", "Reference-driven media work spanning script, assets, audio, render and validation.", "/factories/video"],
      ["Software", "Bounded repository engineering with reviewed code, tests and change evidence.", "/factories/software"],
      ["App", "Application planning and bounded build, test and release-readiness work.", "/factories/app"],
      ["Research / Data", "Source-grounded research and structured analysis with reviewable provenance.", "/factories/research-data"],
      ["Security", "Authorized defensive assessment and remediation work inside explicit scope.", "/factories/security"],
      ["Creative / Document", "Controlled document composition, validation and reviewable export paths.", "/factories/creative-document"],
      ["Commerce / Growth", "Evidence-backed growth proposals and review-gated commercial work.", "/factories/commerce-growth"],
      ["Personal Operations", "Repeatable personal workflows whose consequential side effects remain separately governed.", "/factories/personal-operations"],
    ],
    processEyebrow: "How it works",
    processTitle: "A clear path from goal to finished work.",
    process: [["01", "Goal", "Tell ILAIOS the result you want."], ["02", "Manage", "ILAIOS scopes the permitted work and dependencies."], ["03", "Produce", "The required production work is carried out inside those boundaries."], ["04", "Verify", "Applicable checks evaluate the result."], ["05", "Deliver", "Accepted work is returned with reviewable evidence."]],
    controlEyebrow: "Built-in control",
    controlTitle: "Powerful execution should still have clear boundaries.",
    controlLead: "Identity, permissions, approvals and evidence remain part of the ILAIOS control model. Technical details live in Architecture and Documentation; the product experience stays outcome-first.",
    architecture: "Explore the architecture",
    closeEyebrow: "Start with the outcome",
    closeTitle: "What do you want ILAIOS to finish?",
    closePrimary: "Explore production outcomes",
    closeSecondary: "See capabilities",
  },
  tr: {
    eyebrow: "Hedeften bitmiş sonuca",
    title: "Ne istediğini anlat. ILAIOS işi yönetip doğrulanmış sonuca taşısın.",
    lead: "Tek bir sonuçla başla. ILAIOS gereken işi koordine eder, gerekli kontrolleri uygular, sonucu doğrular ve kanıtı teslimatla birlikte tutar.",
    primary: "ILAIOS neler üretebilir?",
    secondary: "Nasıl çalışır?",
    proof: [["Tek hedef", "Araçları değil, istediğin sonucu tarif et."], ["Yönetilen yürütme", "İş açık izinler ve kontroller içinde kalır."], ["Kontrollü teslim", "Sonuç, teslimden önce geçerli kontrollerle değerlendirilir."]],
    outcomesEyebrow: "Dokuz üretim alanı",
    outcomesTitle: "Tek ürün. Dokuz yönetilen üretim alanı.",
    outcomesLead: "İhtiyacın olan sonucu seç. ILAIOS dokuz sınırlandırılmış üretim alanındaki işi, her aracı ayrı ayrı işletmeni gerektirmeden koordine edebilir.",
    outcomes: [
      ["Web", "Web siteleri ve site revizyonları; yapı, uygulama, tarayıcı, erişilebilirlik ve yayın kontrolleriyle.", "/tr/factories/web"],
      ["Video / Medya", "Referans odaklı medya işi; senaryo, varlıklar, ses, render ve doğrulama adımlarıyla.", "/tr/factories/video"],
      ["Yazılım", "Sınırları belirli repository mühendisliği; incelenmiş kod, testler ve değişiklik kanıtıyla.", "/tr/factories/software"],
      ["Uygulama", "Uygulama planlama ve sınırlandırılmış build, test ve release-readiness çalışması.", "/tr/factories/app"],
      ["Araştırma / Veri", "Kaynak temelli araştırma ve incelenebilir kaynak kökeniyle yapılandırılmış analiz.", "/tr/factories/research-data"],
      ["Güvenlik", "Açık yetki kapsamı içinde savunma odaklı değerlendirme ve düzeltme çalışması.", "/tr/factories/security"],
      ["Creative / Doküman", "Kontrollü doküman oluşturma, doğrulama ve incelenebilir dışa aktarma yolları.", "/tr/factories/creative-document"],
      ["Commerce / Büyüme", "Kanıta dayalı büyüme önerileri ve inceleme kapılı ticari çalışma.", "/tr/factories/commerce-growth"],
      ["Kişisel Operasyon", "Önemli dış etkileri ayrıca yönetilen tekrarlanabilir kişisel iş akışları.", "/tr/factories/personal-operations"],
    ],
    processEyebrow: "Nasıl çalışır?",
    processTitle: "Hedeften bitmiş işe uzanan açık bir yol.",
    process: [["01", "Hedef", "İstediğin sonucu ILAIOS'a anlat."], ["02", "Yönet", "ILAIOS izin verilen işi ve bağımlılıkları sınırlar."], ["03", "Üret", "Gerekli üretim işi bu sınırlar içinde yürütülür."], ["04", "Doğrula", "Geçerli kontroller sonucu değerlendirir."], ["05", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."]],
    controlEyebrow: "Yerleşik kontrol",
    controlTitle: "Güçlü yürütmenin sınırları da açık olmalı.",
    controlLead: "Kimlik, izinler, onaylar ve kanıt ILAIOS kontrol modelinin parçası olarak kalır. Teknik ayrıntılar Mimari ve Dokümantasyon'da bulunur; ürün deneyimi sonuç odaklı kalır.",
    architecture: "Mimariyi incele",
    closeEyebrow: "Sonuçla başla",
    closeTitle: "ILAIOS'un neyi bitirmesini istiyorsun?",
    closePrimary: "Üretim sonuçlarını keşfet",
    closeSecondary: "Yetenekleri gör",
  },
} as const;

export default function HomePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="homepage-v2 home-hero shell" data-visual-role="home-hero" style={{ backgroundColor: "var(--bg)" }}>
      <div className="home-hero-copy" data-visual-role="homepage-v2-authoritative"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.primary}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link></div></div>
      <ProductExperience locale={locale} />
    </section>
    <section className="proof-strip"><div className="shell proof-strip-grid">{c.proof.map(([title, text]) => <div key={title}><strong>{title}</strong><span>{text}</span></div>)}</div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.outcomesEyebrow}</div><h2>{c.outcomesTitle}</h2></div><p>{c.outcomesLead}</p></div><div className="outcome-showcase home-output-index-v2">{c.outcomes.map(([title,text,href], index) => <Link className="outcome-row" href={href} key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{title}</h3><p>{text}</p></div><strong aria-hidden="true">→</strong></Link>)}</div></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{c.processEyebrow}</div><h2>{c.processTitle}</h2></div></div><div className="process-rail home-process-rail-v2" data-visual-role="five-step-execution">{c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section home-control-ledger-v2"><div className="shell evidence-story"><div className="evidence-story-copy"><div className="eyebrow">{c.controlEyebrow}</div><h2>{c.controlTitle}</h2><p>{c.controlLead}</p><Link className="text-link" href={`${base}/architecture`}>{c.architecture} →</Link></div><GovernanceEvidence locale={locale} /></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.closeEyebrow}</div><h2>{c.closeTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/factories`}>{c.closePrimary}</Link><Link className="button secondary" href={`${base}/capabilities`}>{c.closeSecondary}</Link></div></div></section>
  </>;
}
