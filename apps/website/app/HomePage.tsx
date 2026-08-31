import Link from "next/link";
import GovernanceEvidence from "./GovernanceEvidence";
import ProductExperience from "./ProductExperience";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Governed AI Operating System",
    title: "Describe the outcome. ILAIOS governs the work to a verified result.",
    lead: "One request can coordinate research and digital production while identity, policy, approvals, validation and evidence remain under one authoritative control plane.",
    primary: "Explore production",
    secondary: "How ILAIOS works",
    proof: [
      ["One authority", "Policy, approvals and evidence stay shared."],
      ["Outcome first", "You describe the result instead of operating providers."],
      ["Verified delivery", "Acceptance follows checks and evidence, not a model claim."],
    ],
    thesisEyebrow: "Product thesis",
    thesisTitle: "Simple at the surface. Explicit control underneath.",
    thesisBody: "ILAIOS resolves an authenticated goal into bounded work. Models, tools and providers can change; execution authority does not move into them.",
    processEyebrow: "Execution",
    processTitle: "A controlled path from intent to accepted result.",
    process: [
      ["01", "Goal", "Authenticated intent and context enter the system."],
      ["02", "Plan", "Dependencies, policy and required approvals constrain the path."],
      ["03", "Execute", "Admitted capabilities perform only scoped work."],
      ["04", "Verify", "Tests, QA and acceptance criteria evaluate the output."],
      ["05", "Deliver", "Accepted work is surfaced with reviewable evidence."],
    ],
    outputEyebrow: "Production paths",
    outputTitle: "Different outcomes. One governance spine.",
    outputLead: "Production maturity varies by capability. The website does not present in-development work as production-ready.",
    outputs: [
      ["Web", "Websites and web products", "/factories/web"],
      ["Software", "Repository-aware implementation and verification", "/factories/software"],
      ["Video", "Reference-aware media production and QA", "/factories/video"],
      ["App", "Cross-platform application production", "/factories/app"],
      ["Research", "Source-grounded analysis and evidence", "/factories/research-data"],
    ],
    trustEyebrow: "Control",
    trustTitle: "Execution power never becomes execution authority.",
    trustBody: "Identity and tenant scope, policy, approvals, controlled execution, validation, audit and evidence remain inside ILAIOS.",
    trustLink: "Architecture",
    evidenceEyebrow: "Evidence",
    evidenceTitle: "Generated is not finished.",
    evidenceBody: "A finished result must satisfy the checks that apply to its workload. The evidence stays reviewable instead of being reduced to a success message.",
    closeEyebrow: "Start with the outcome",
    closeTitle: "Choose what you want ILAIOS to produce.",
    capabilities: "Capabilities",
  },
  tr: {
    eyebrow: "Yönetilen Yapay Zekâ İşletim Sistemi",
    title: "Sonucu tarif et. ILAIOS işi yönetip doğrulanmış sonuca taşısın.",
    lead: "Tek bir istek araştırma ve dijital üretimi koordine edebilir; kimlik, politika, onaylar, doğrulama ve kanıt tek yetkili kontrol katmanında kalır.",
    primary: "Üretim yollarını incele",
    secondary: "ILAIOS nasıl çalışır?",
    proof: [
      ["Tek yetki", "Politika, onaylar ve kanıt ortak kalır."],
      ["Sonuç odaklı", "Sağlayıcıları işletmek yerine istediğin sonucu tarif edersin."],
      ["Doğrulanmış teslim", "Kabul model iddiasına değil kontrol ve kanıta dayanır."],
    ],
    thesisEyebrow: "Ürün tezi",
    thesisTitle: "Yüzeyde sade. Altında açık kontrol.",
    thesisBody: "ILAIOS, kimliği doğrulanmış hedefi sınırlandırılmış işe dönüştürür. Modeller, araçlar ve sağlayıcılar değişebilir; yürütme yetkisi onlara taşınmaz.",
    processEyebrow: "Yürütme",
    processTitle: "Niyetten kabul edilmiş sonuca kontrollü bir yol.",
    process: [
      ["01", "Hedef", "Kimliği doğrulanmış niyet ve bağlam sisteme girer."],
      ["02", "Plan", "Bağımlılıklar, politika ve gerekli onaylar yolu sınırlar."],
      ["03", "Yürüt", "Kabul edilmiş yetenekler yalnız kapsamlı işi yapar."],
      ["04", "Doğrula", "Testler, QA ve kabul ölçütleri çıktıyı değerlendirir."],
      ["05", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."],
    ],
    outputEyebrow: "Üretim yolları",
    outputTitle: "Farklı sonuçlar. Tek yönetişim omurgası.",
    outputLead: "Üretim olgunluğu yeteneğe göre değişir. Site geliştirme aşamasındaki işi production-ready gibi sunmaz.",
    outputs: [
      ["Web", "Web siteleri ve web ürünleri", "/tr/factories/web"],
      ["Yazılım", "Repository-aware implementasyon ve doğrulama", "/tr/factories/software"],
      ["Video", "Referans-aware medya üretimi ve QA", "/tr/factories/video"],
      ["Uygulama", "Cross-platform uygulama üretimi", "/tr/factories/app"],
      ["Araştırma", "Kaynak temelli analiz ve kanıt", "/tr/factories/research-data"],
    ],
    trustEyebrow: "Kontrol",
    trustTitle: "Yürütme gücü, yürütme yetkisine dönüşmez.",
    trustBody: "Kimlik ve tenant kapsamı, politika, onaylar, kontrollü yürütme, doğrulama, audit ve kanıt ILAIOS içinde kalır.",
    trustLink: "Mimari",
    evidenceEyebrow: "Kanıt",
    evidenceTitle: "Üretilmiş olmak, bitmiş olmak değildir.",
    evidenceBody: "Bitmiş sonuç ilgili iş yükünün gerektirdiği kontrolleri geçmelidir. Kanıt, tek bir başarı mesajına indirgenmeden incelenebilir kalır.",
    closeEyebrow: "Sonuçla başla",
    closeTitle: "ILAIOS'un ne üretmesini istediğini seç.",
    capabilities: "Yetenekler",
  },
} as const;

export default function HomePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";

  return <div className="homepage-v2" data-visual-role="homepage-v2-authoritative">
    <section className="home-hero-v2 shell" data-visual-role="home-hero" style={{ paddingTop: "48px", paddingBottom: "48px" }}>
      <div className="home-hero-v2-copy">
        <div className="eyebrow">{c.eyebrow}</div>
        <h1 style={{ fontSize: "clamp(2.2rem, 3.35vw, 3rem)", lineHeight: 1 }}>{c.title}</h1>
        <p className="lead">{c.lead}</p>
        <div className="actions">
          <Link className="button" href={`${base}/factories`}>{c.primary}</Link>
          <Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link>
        </div>
      </div>
      <div className="home-product-surface"><ProductExperience locale={locale} /></div>
    </section>

    <section className="home-proof-v2">
      <div className="shell home-proof-v2-grid">
        {c.proof.map(([title, text]) => <div key={title}><strong>{title}</strong><span>{text}</span></div>)}
      </div>
    </section>

    <section className="section home-thesis-v2">
      <div className="shell home-editorial-v2">
        <div><div className="eyebrow">{c.thesisEyebrow}</div><h2>{c.thesisTitle}</h2></div>
        <p>{c.thesisBody}</p>
      </div>
    </section>

    <section className="section home-process-v2">
      <div className="shell">
        <div className="home-section-heading-v2"><div className="eyebrow">{c.processEyebrow}</div><h2>{c.processTitle}</h2></div>
        <div className="home-process-rail-v2" data-visual-role="five-step-execution">
          {c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}
        </div>
      </div>
    </section>

    <section className="section home-output-v2">
      <div className="shell">
        <div className="home-editorial-v2">
          <div><div className="eyebrow">{c.outputEyebrow}</div><h2>{c.outputTitle}</h2></div>
          <p>{c.outputLead}</p>
        </div>
        <div className="home-output-index-v2">
          {c.outputs.map(([title, text, href], index) => <Link href={href} key={href}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{text}</small><i aria-hidden="true">→</i></Link>)}
        </div>
      </div>
    </section>

    <section className="section home-control-v2">
      <div className="shell home-control-grid-v2">
        <div><div className="eyebrow">{c.trustEyebrow}</div><h2>{c.trustTitle}</h2><p>{c.trustBody}</p><Link className="text-link" href={`${base}/architecture`}>{c.trustLink} →</Link></div>
        <div className="home-control-ledger-v2" aria-label={c.trustEyebrow}>
          <span>Identity / Tenant</span><span>Policy / Approval</span><span>Controlled execution</span><span>Validation</span><span>Audit / Evidence</span>
        </div>
      </div>
    </section>

    <section className="section home-evidence-v2">
      <div className="shell home-evidence-grid-v2">
        <div><div className="eyebrow">{c.evidenceEyebrow}</div><h2>{c.evidenceTitle}</h2><p>{c.evidenceBody}</p></div>
        <GovernanceEvidence locale={locale} />
      </div>
    </section>

    <section className="section compact-section">
      <div className="shell compact-cta">
        <div><div className="eyebrow">{c.closeEyebrow}</div><h2>{c.closeTitle}</h2></div>
        <div className="actions"><Link className="button" href={`${base}/factories`}>{c.primary}</Link><Link className="button secondary" href={`${base}/capabilities`}>{c.capabilities}</Link></div>
      </div>
    </section>
  </div>;
}
