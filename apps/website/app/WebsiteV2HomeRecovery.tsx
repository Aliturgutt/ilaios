import Link from "next/link";
import SuppliedVisual from "./SuppliedVisual";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Governed Digital Operating Platform",
    title: "Turn one business goal into governed, evidence-backed work.",
    lead: "ILAIOS coordinates shared capabilities and specialized production paths through one controlled execution authority, then validates the result before delivery.",
    primary: "Explore production",
    secondary: "How it works",
    visualAlt: "ILAIOS operating model from business intent through governed execution, specialized production paths and validation to an evidence-backed outcome.",
    visualCaption: "One governed authority coordinates shared capabilities and specialized production paths without creating parallel execution authority.",
    thesisEyebrow: "Platform",
    thesisTitle: "One request at the surface. Explicit control underneath.",
    thesisBody: "Users should not have to choose models, providers or internal agents. ILAIOS resolves the requested outcome into bounded work while identity, policy, approvals, routing, validation and evidence remain shared controls.",
    processEyebrow: "How it works",
    processTitle: "A short path from intent to accepted result.",
    process: [
      ["01", "Describe the outcome", "Start with the business result, context and references."],
      ["02", "Govern the plan", "Identity, policy, approvals and dependencies constrain execution."],
      ["03", "Execute the work", "Shared capabilities and production paths perform only admitted tasks."],
      ["04", "Validate before delivery", "Tests, QA and acceptance evidence determine whether the result is ready."],
    ],
    trustEyebrow: "Security and control",
    trustTitle: "Execution power does not become execution authority.",
    trustBody: "Models, tools and providers are replaceable implementation resources. The canonical authority remains inside ILAIOS: identity and tenant scope, policy, approvals, controlled execution, validation, audit and evidence.",
    factoryEyebrow: "Production",
    factoryTitle: "Different outcomes. One governance spine.",
    factories: [
      ["Web", "Websites and web products through research, design, implementation and browser QA."],
      ["Software", "Repository-aware software implementation with testing and evidence."],
      ["App", "Cross-platform application production is being expanded through the existing governed runtime."],
      ["Video", "Reference-aware video production through the canonical media pipeline and QA."],
    ],
    maturity: "Current maturity varies by capability. In-development work is not presented as production-ready.",
    evidenceEyebrow: "Evidence",
    evidenceTitle: "Generated is not finished.",
    evidenceBody: "ILAIOS separates creation from acceptance. A result is delivered with the verification evidence that applies to that workload, not with a model-generated claim of success.",
    closeTitle: "Understand the platform, then choose the outcome you need.",
    architecture: "Platform architecture",
    capabilities: "Capabilities",
  },
  tr: {
    eyebrow: "Yönetilen Dijital Çalışma Platformu",
    title: "Tek bir iş hedefini yönetilen ve kanıta dayalı çalışmaya dönüştürün.",
    lead: "ILAIOS, paylaşılan yetenekleri ve uzmanlaşmış üretim yollarını tek kontrollü yürütme yetkisi üzerinden koordine eder ve sonucu teslimden önce doğrular.",
    primary: "Üretim yollarını incele",
    secondary: "Nasıl çalışır?",
    visualAlt: "ILAIOS çalışma modelinde iş hedefinin yönetilen yürütme, uzmanlaşmış üretim yolları ve doğrulama üzerinden kanıta dayalı sonuca ilerleyişi.",
    visualCaption: "Tek yönetilen yetki, paralel bir yürütme otoritesi oluşturmadan paylaşılan yetenekleri ve uzmanlaşmış üretim yollarını koordine eder.",
    thesisEyebrow: "Platform",
    thesisTitle: "Yüzeyde tek istek. Altında açık kontrol.",
    thesisBody: "Kullanıcı model, sağlayıcı veya dahili ajan seçmek zorunda kalmamalı. ILAIOS istenen sonucu sınırlandırılmış işlere çözümlerken kimlik, politika, onaylar, yönlendirme, doğrulama ve kanıt ortak kontrol olarak kalır.",
    processEyebrow: "Nasıl çalışır?",
    processTitle: "Niyetten kabul edilmiş sonuca kısa ve kontrollü bir yol.",
    process: [
      ["01", "Sonucu tarif et", "İş sonucu, bağlam ve referanslarla başla."],
      ["02", "Planı yönet", "Kimlik, politika, onaylar ve bağımlılıklar yürütmeyi sınırlar."],
      ["03", "İşi yürüt", "Paylaşılan yetenekler ve üretim yolları yalnız kabul edilmiş görevleri yapar."],
      ["04", "Teslimden önce doğrula", "Testler, QA ve kabul kanıtı sonucun hazır olup olmadığını belirler."],
    ],
    trustEyebrow: "Güvenlik ve kontrol",
    trustTitle: "Yürütme gücü, yürütme yetkisine dönüşmez.",
    trustBody: "Modeller, araçlar ve sağlayıcılar değiştirilebilir uygulama kaynaklarıdır. Kanonik yetki ILAIOS içinde kalır: kimlik ve tenant kapsamı, politika, onaylar, kontrollü yürütme, doğrulama, audit ve kanıt.",
    factoryEyebrow: "Üretim",
    factoryTitle: "Farklı sonuçlar. Tek yönetişim omurgası.",
    factories: [
      ["Web", "Araştırma, tasarım, implementasyon ve browser QA üzerinden web sitesi ve web ürünleri."],
      ["Software", "Repository-aware yazılım implementasyonu, test ve kanıt."],
      ["App", "Cross-platform uygulama üretimi mevcut yönetilen runtime üzerinden genişletiliyor."],
      ["Video", "Kanonik medya pipeline'ı ve QA üzerinden referans-aware video üretimi."],
    ],
    maturity: "Gerçek olgunluk yeteneğe göre değişir. Geliştirme aşamasındaki işler production-ready gibi sunulmaz.",
    evidenceEyebrow: "Kanıt",
    evidenceTitle: "Üretilmiş olmak, bitmiş olmak değildir.",
    evidenceBody: "ILAIOS üretim ile kabulü ayırır. Sonuç, modelin başarı iddiasıyla değil; ilgili iş yüküne uygulanan doğrulama kanıtıyla teslim edilir.",
    closeTitle: "Platformu anlayın, sonra ihtiyacınız olan sonucu seçin.",
    architecture: "Platform mimarisi",
    capabilities: "Yetenekler",
  },
} as const;

export default function WebsiteV2HomeRecovery({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";

  return <main className="v2-recovery-home">
    <section className="v2-hero shell">
      <div className="v2-hero-copy">
        <div className="eyebrow">{c.eyebrow}</div>
        <h1>{c.title}</h1>
        <p className="lead">{c.lead}</p>
        <div className="actions">
          <Link className="button" href={`${base}/factories`}>{c.primary}</Link>
          <Link className="button secondary" href={`${base}/how-it-works`}>{c.secondary}</Link>
        </div>
      </div>
      <div className="v2-hero-media">
        <SuppliedVisual priority className="v2-hero-visual" light="/website-v2/homepage-light.avif" dark="/website-v2/homepage-dark.avif" alt={c.visualAlt} caption={c.visualCaption} />
      </div>
    </section>

    <section className="v2-editorial shell">
      <div className="v2-index">01</div>
      <div>
        <div className="eyebrow">{c.thesisEyebrow}</div>
        <h2>{c.thesisTitle}</h2>
        <p>{c.thesisBody}</p>
      </div>
    </section>

    <section className="v2-process-section">
      <div className="shell">
        <div className="v2-section-heading">
          <div className="eyebrow">{c.processEyebrow}</div>
          <h2>{c.processTitle}</h2>
        </div>
        <div className="v2-process-rail">
          {c.process.map(([n, title, text]) => <article key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </div>
    </section>

    <section className="v2-split shell">
      <div className="v2-index">02</div>
      <div className="v2-split-copy">
        <div className="eyebrow">{c.trustEyebrow}</div>
        <h2>{c.trustTitle}</h2>
        <p>{c.trustBody}</p>
        <Link className="text-link" href={`${base}/architecture`}>{c.architecture} →</Link>
      </div>
      <div className="v2-control-rail" aria-label={c.trustEyebrow}>
        <span>Identity / Tenant</span><span>Policy / Approval</span><span>Controlled execution</span><span>Validation</span><span>Audit / Evidence</span>
      </div>
    </section>

    <section className="v2-factories">
      <div className="shell">
        <div className="v2-section-heading compact">
          <div className="eyebrow">{c.factoryEyebrow}</div>
          <h2>{c.factoryTitle}</h2>
        </div>
        <div className="v2-factory-index">
          {c.factories.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{text}</p></article>)}
        </div>
        <p className="v2-maturity">{c.maturity}</p>
      </div>
    </section>

    <section className="v2-editorial shell v2-evidence">
      <div className="v2-index">03</div>
      <div>
        <div className="eyebrow">{c.evidenceEyebrow}</div>
        <h2>{c.evidenceTitle}</h2>
        <p>{c.evidenceBody}</p>
      </div>
    </section>

    <section className="v2-close shell">
      <h2>{c.closeTitle}</h2>
      <div className="actions"><Link className="button" href={`${base}/architecture`}>{c.architecture}</Link><Link className="button secondary" href={`${base}/capabilities`}>{c.capabilities}</Link></div>
    </section>

    <style>{`
      .v2-recovery-home{--v2-rule:var(--line);overflow:hidden}
      .v2-hero{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(36px,6vw,84px);align-items:center;padding-top:clamp(72px,9vw,128px);padding-bottom:clamp(72px,9vw,120px)}
      .v2-hero-copy{max-width:680px}.v2-hero h1{max-width:13ch;font-size:clamp(3rem,6vw,6.2rem);line-height:.95;letter-spacing:-.052em;margin:18px 0 24px}.v2-hero .lead{max-width:58ch;font-size:clamp(1.05rem,1.6vw,1.28rem);line-height:1.65}.v2-hero .actions{margin-top:30px}
      .v2-hero-media{min-width:0;max-width:860px;justify-self:end;width:100%}.v2-hero-visual{border-radius:14px!important}.v2-hero-visual figcaption{font-size:.78rem!important}
      .v2-editorial{display:grid;grid-template-columns:80px minmax(0,760px);gap:clamp(24px,5vw,72px);padding-top:clamp(76px,10vw,136px);padding-bottom:clamp(76px,10vw,136px);border-top:1px solid var(--v2-rule)}
      .v2-index{font-size:.76rem;letter-spacing:.16em;color:var(--muted);padding-top:8px}.v2-editorial h2,.v2-split h2,.v2-section-heading h2,.v2-close h2{font-size:clamp(2rem,4vw,3.8rem);line-height:1.03;letter-spacing:-.038em;margin:14px 0 22px}.v2-editorial p,.v2-split p{max-width:65ch;font-size:1.05rem;line-height:1.75;color:var(--muted)}
      .v2-process-section{border-top:1px solid var(--v2-rule);border-bottom:1px solid var(--v2-rule);background:var(--v2-surface-strong);padding:clamp(72px,9vw,116px) 0}.v2-section-heading{max-width:860px;margin-bottom:clamp(40px,6vw,68px)}.v2-section-heading.compact{max-width:720px}
      .v2-process-rail{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--v2-rule)}.v2-process-rail article{padding:28px 28px 8px 0;border-right:1px solid var(--v2-rule);min-height:220px}.v2-process-rail article+article{padding-left:28px}.v2-process-rail article:last-child{border-right:0}.v2-process-rail span,.v2-factory-index span{font-size:.72rem;letter-spacing:.16em;color:var(--muted)}.v2-process-rail h3,.v2-factory-index h3{font-size:1.08rem;margin:52px 0 12px}.v2-process-rail p,.v2-factory-index p{color:var(--muted);line-height:1.65;font-size:.93rem}
      .v2-split{display:grid;grid-template-columns:80px minmax(0,1fr) minmax(280px,.65fr);gap:clamp(24px,5vw,72px);align-items:start;padding-top:clamp(80px,10vw,140px);padding-bottom:clamp(80px,10vw,140px)}.v2-split-copy .text-link{display:inline-block;margin-top:18px}.v2-control-rail{border-top:1px solid var(--v2-rule)}.v2-control-rail span{display:block;padding:17px 0;border-bottom:1px solid var(--v2-rule);font-size:.88rem;letter-spacing:.03em}
      .v2-factories{background:var(--v2-surface-strong);border-top:1px solid var(--v2-rule);border-bottom:1px solid var(--v2-rule);padding:clamp(76px,9vw,120px) 0}.v2-factory-index{display:grid;grid-template-columns:repeat(2,1fr);border-top:1px solid var(--v2-rule)}.v2-factory-index article{display:grid;grid-template-columns:56px minmax(100px,.38fr) minmax(0,1fr);gap:18px;padding:27px 0;border-bottom:1px solid var(--v2-rule)}.v2-factory-index article:nth-child(odd){padding-right:32px;border-right:1px solid var(--v2-rule)}.v2-factory-index article:nth-child(even){padding-left:32px}.v2-factory-index h3{margin:0}.v2-factory-index p{margin:0}.v2-maturity{margin:24px 0 0;max-width:72ch;color:var(--muted);font-size:.86rem;line-height:1.6}
      .v2-evidence{border-top:0}.v2-close{display:flex;justify-content:space-between;gap:40px;align-items:flex-end;padding-top:clamp(60px,8vw,104px);padding-bottom:clamp(72px,9vw,120px);border-top:1px solid var(--v2-rule)}.v2-close h2{max-width:18ch;margin:0}.v2-close .actions{flex-shrink:0}
      @media(max-width:980px){.v2-hero{grid-template-columns:1fr;gap:44px}.v2-hero-copy{max-width:760px}.v2-hero-media{max-width:780px;justify-self:start}.v2-process-rail{grid-template-columns:repeat(2,1fr)}.v2-process-rail article:nth-child(2){border-right:0}.v2-process-rail article:nth-child(n+3){border-top:1px solid var(--v2-rule)}.v2-split{grid-template-columns:64px 1fr}.v2-control-rail{grid-column:2}.v2-factory-index{grid-template-columns:1fr}.v2-factory-index article:nth-child(n){padding-left:0;padding-right:0;border-right:0}}
      @media(max-width:620px){.v2-hero{padding-top:58px;padding-bottom:72px;gap:34px}.v2-hero h1{font-size:clamp(2.65rem,13vw,4.2rem);max-width:12ch}.v2-hero-media{width:100%}.v2-editorial,.v2-split{grid-template-columns:1fr;gap:18px}.v2-index{padding-top:0}.v2-control-rail{grid-column:1}.v2-process-rail{grid-template-columns:1fr}.v2-process-rail article:nth-child(n){padding:24px 0;border-right:0;border-top:1px solid var(--v2-rule);min-height:0}.v2-process-rail h3{margin:22px 0 8px}.v2-factory-index article{grid-template-columns:40px 1fr;gap:10px 14px}.v2-factory-index article p{grid-column:2}.v2-close{display:block}.v2-close .actions{margin-top:28px}}
    `}</style>
  </main>;
}
