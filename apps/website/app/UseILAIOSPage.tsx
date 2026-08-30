import Link from "next/link";
import ThemedDiagram from "./ThemedDiagram";
import ProductExperience from "./ProductExperience";

type Locale = "en" | "tr";
type FactoryStatus = "preview" | "development";

type Factory = {
  name: string;
  description: string;
  status: FactoryStatus;
  statusLabel: string;
  href: string;
  example: string;
};

const copy = {
  en: {
    eyebrow: "Use ILAIOS",
    title: "One goal. Choose what you want to create.",
    lead: "Describe the outcome in normal language, add useful context, and let ILAIOS plan and govern the production path. Internal providers and routing stay behind the product boundary.",
    howTitle: "From request to reviewable delivery.",
    howLead: "You do not need to operate models, providers or internal tools. You define the outcome and the acceptance intent; ILAIOS keeps execution bounded and evidence-linked.",
    steps: [
      ["01", "Describe", "State the finished outcome you want."],
      ["02", "Add context", "Attach brand assets, references, documents, an existing product or constraints when useful."],
      ["03", "Plan", "ILAIOS decomposes the work into bounded steps and dependencies."],
      ["04", "Govern", "Policy, risk, budget and approval requirements are checked before admitted work proceeds."],
      ["05", "Execute & verify", "The appropriate factory runs the work and required acceptance checks evaluate the result."],
      ["06", "Receive", "Accepted work is returned with reviewable evidence; unresolved work stops or enters bounded repair."],
    ],
    inputEyebrow: "What should I provide?",
    inputTitle: "Structured input helps ILAIOS understand the result you actually want.",
    inputCaption: "Prompt, brand assets, references, existing product context, documents, requirements, constraints and acceptance criteria can all be useful inputs. You only provide what the task needs.",
    createEyebrow: "What can I create?",
    createTitle: "Factories specialize the production path without becoming separate authorities.",
    availability: "Current availability",
    preview: "Preview",
    development: "In development",
    truth: "Status labels describe current public readiness conservatively. A target factory outcome is not a claim that every provider, platform or release path is production-verified today.",
    examplesEyebrow: "Example prompts",
    examplesTitle: "Start with the result, not the implementation stack.",
    demoEyebrow: "Product-flow concept",
    demoTitle: "The interface can keep progress visible without exposing internal routing details.",
    demoCaption: "Static illustrative workflow crop from the supplied product mockup. It is not live telemetry and does not represent a production run.",
    boundaryEyebrow: "What ILAIOS does not do",
    boundaryTitle: "Capability does not become authority.",
    boundaryText: "ILAIOS does not treat a model, provider, skill or factory as permission to act. Sensitive side effects remain subject to identity, tenant scope, policy, approval, tool and validation boundaries.",
    works: "How ILAIOS works",
    factories: "Explore factories",
    factoryData: [
      { name: "Web Factory", description: "New websites, site upgrades and desktop-style web products.", status: "preview", statusLabel: "Preview", href: "/factories/web", example: "Build a premium bilingual website for my architecture studio." },
      { name: "Video / Media Factory", description: "Scripted, reference-driven media production with validation and evidence.", status: "preview", statusLabel: "Preview", href: "/factories/video", example: "Create a 20-second cinematic launch video using these product images." },
      { name: "Software Factory", description: "Bounded repository engineering, tests, review and release evidence.", status: "preview", statusLabel: "Preview", href: "/factories/software", example: "Implement this repository feature, run the required tests and return the review evidence." },
      { name: "App Factory", description: "Windows-first bounded application outcomes; Android/iOS and Store release remain separate gates.", status: "preview", statusLabel: "Preview", href: "/factories/app", example: "Build a governed appointment application and prepare its release-readiness checklist." },
      { name: "Research & Data", description: "Grounded research, structured findings and provenance-first analysis.", status: "development", statusLabel: "In development", href: "/factories/research-data", example: "Research this market and return a source-grounded decision brief." },
      { name: "Security", description: "Authorized defensive assessment and remediation workflows.", status: "development", statusLabel: "In development", href: "/factories/security", example: "Review this authorized system scope for security risks and remediation priorities." },
      { name: "Creative & Documents", description: "Controlled document composition and evidence-linked export paths.", status: "development", statusLabel: "In development", href: "/factories/creative-document", example: "Turn these approved source documents into a reviewable executive report." },
      { name: "Commerce & Growth", description: "Evidence-backed proposals, drafts and review-gated growth work.", status: "development", statusLabel: "In development", href: "/factories/commerce-growth", example: "Prepare a growth experiment plan from these verified performance inputs." },
      { name: "Personal Operations", description: "Reviewable personal workflows with side effects separately governed.", status: "development", statusLabel: "In development", href: "/factories/personal-operations", example: "Prepare a reviewable weekly operations plan from these priorities." },
    ] as readonly Factory[],
  },
  tr: {
    eyebrow: "ILAIOS'u Kullan",
    title: "Tek hedef. Ne oluşturmak istediğini seç.",
    lead: "İstediğin sonucu normal dille tarif et, yararlı bağlamı ekle ve üretim yolunu ILAIOS'un planlayıp yönetmesine bırak. İç sağlayıcılar ve yönlendirme ayrıntıları ürün sınırının arkasında kalır.",
    howTitle: "İstekten incelenebilir teslime.",
    howLead: "Model, sağlayıcı veya dahili araç işletmek zorunda değilsin. Sonucu ve kabul niyetini tanımlarsın; ILAIOS yürütmeyi sınırlandırılmış ve kanıta bağlı tutar.",
    steps: [
      ["01", "Tarif et", "Bitmesini istediğin sonucu belirt."],
      ["02", "Bağlam ekle", "Gerektiğinde marka varlıkları, referanslar, dokümanlar, mevcut ürün veya kısıtları ekle."],
      ["03", "Planla", "ILAIOS işi sınırlandırılmış adımlara ve bağımlılıklara ayırır."],
      ["04", "Yönet", "İş ilerlemeden önce politika, risk, bütçe ve gerekli onaylar kontrol edilir."],
      ["05", "Yürüt & doğrula", "Uygun factory işi yürütür ve gerekli kabul kontrolleri sonucu değerlendirir."],
      ["06", "Teslim al", "Kabul edilen iş incelenebilir kanıtla döner; çözülemeyen iş durur veya bounded repair'e girer."],
    ],
    inputEyebrow: "Ne sağlamalıyım?",
    inputTitle: "Yapılandırılmış girdiler ILAIOS'un gerçekten istediğin sonucu anlamasına yardımcı olur.",
    inputCaption: "Prompt, marka varlıkları, referanslar, mevcut ürün bağlamı, dokümanlar, gereksinimler, kısıtlar ve kabul kriterleri yararlı olabilir. Yalnızca işin ihtiyaç duyduğu girdileri sağlarsın.",
    createEyebrow: "Neler oluşturabilirim?",
    createTitle: "Factory'ler üretim yolunu uzmanlaştırır; ayrı yetki otoritelerine dönüşmez.",
    availability: "Güncel erişilebilirlik",
    preview: "Önizleme",
    development: "Geliştiriliyor",
    truth: "Durum etiketleri güncel public readiness seviyesini ihtiyatlı biçimde gösterir. Hedef factory çıktısı, her sağlayıcı, platform veya release yolunun bugün production-verified olduğu iddiası değildir.",
    examplesEyebrow: "Örnek promptlar",
    examplesTitle: "Teknik yığınla değil, istediğin sonuçla başla.",
    demoEyebrow: "Ürün akışı konsepti",
    demoTitle: "Arayüz ilerlemeyi görünür tutabilir; dahili yönlendirme ayrıntılarını dışarı açmak zorunda değildir.",
    demoCaption: "Sağlanan ürün mockup'ından alınmış statik açıklayıcı workflow kırpımıdır. Canlı telemetri değildir ve production run temsil etmez.",
    boundaryEyebrow: "ILAIOS ne yapmaz?",
    boundaryTitle: "Yetenek, yetkiye dönüşmez.",
    boundaryText: "ILAIOS bir model, sağlayıcı, skill veya factory'yi işlem izni olarak kabul etmez. Hassas dış etkiler kimlik, tenant kapsamı, politika, onay, araç ve doğrulama sınırlarına tabi kalır.",
    works: "ILAIOS nasıl çalışır?",
    factories: "Factory'leri incele",
    factoryData: [
      { name: "Web Factory", description: "Yeni web siteleri, site yükseltmeleri ve desktop-style web ürünleri.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/web", example: "Mimarlık stüdyom için premium, iki dilli bir web sitesi oluştur." },
      { name: "Video / Media Factory", description: "Senaryo ve referans odaklı, doğrulama ve kanıt içeren medya üretimi.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/video", example: "Bu ürün görsellerini kullanarak 20 saniyelik sinematik lansman videosu oluştur." },
      { name: "Software Factory", description: "Sınırlandırılmış repository mühendisliği, test, review ve release kanıtı.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/software", example: "Bu repository özelliğini uygula, gerekli testleri çalıştır ve review evidence döndür." },
      { name: "App Factory", description: "Windows-first bounded uygulama sonuçları; Android/iOS ve Store release ayrı kapılar olarak kalır.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/app", example: "Kontrollü bir randevu uygulaması oluştur ve release-readiness checklist'ini hazırla." },
      { name: "Research & Data", description: "Kaynaklandırılmış araştırma, yapılandırılmış bulgular ve provenance-first analiz.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/research-data", example: "Bu pazarı araştır ve kaynaklara dayalı karar özeti hazırla." },
      { name: "Security", description: "Yetkili savunma değerlendirmesi ve remediation akışları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/security", example: "Bu yetkilendirilmiş sistem kapsamını güvenlik riskleri ve remediation öncelikleri için incele." },
      { name: "Creative & Documents", description: "Kontrollü doküman oluşturma ve kanıta bağlı dışa aktarma yolları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/creative-document", example: "Bu onaylı kaynak dokümanlardan incelenebilir bir yönetici raporu oluştur." },
      { name: "Commerce & Growth", description: "Kanıta dayalı öneriler, taslaklar ve review-gated büyüme çalışmaları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/commerce-growth", example: "Bu doğrulanmış performans girdilerinden bir büyüme deneyi planı hazırla." },
      { name: "Personal Operations", description: "Dış etkileri ayrı yönetilen, incelenebilir kişisel iş akışları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/personal-operations", example: "Bu önceliklerden incelenebilir haftalık operasyon planı hazırla." },
    ] as readonly Factory[],
  },
} as const;

export default function UseILAIOSPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";

  return <>
    <section className="shell page-hero use-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/factories`}>{c.factories}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.works}</Link></div></section>

    <section className="section surface-section"><div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{c.createEyebrow}</div><h2>{c.createTitle}</h2></div><p>{c.truth}</p></div>
      <div className="use-factory-grid">{c.factoryData.map(factory => <article className="use-factory-card" key={factory.href}>
        <div className="use-factory-card-head"><span className={`availability-chip is-${factory.status}`}>{factory.statusLabel}</span><small>{c.availability}</small></div>
        <h3>{factory.name}</h3><p>{factory.description}</p><blockquote>{factory.example}</blockquote><Link className="text-link" href={factory.href}>{locale === "tr" ? "Ayrıntıyı aç" : "Open details"} →</Link>
      </article>)}</div>
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{c.inputEyebrow}</div><h2>{c.inputTitle}</h2></div><p>{c.inputCaption}</p></div>
      <ThemedDiagram light="/visuals/intake-light.avif" dark="/visuals/intake-dark.avif" alt={locale === "tr" ? "ILAIOS için sağlanabilecek girdileri gösteren ürün intake diyagramı" : "ILAIOS product intake diagram showing the kinds of inputs a user can provide"} aspect="portrait" />
    </div></section>

    <section className="section surface-section"><div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kullanım akışı" : "Usage flow"}</div><h2>{c.howTitle}</h2></div><p>{c.howLead}</p></div>
      <div className="use-step-grid">{c.steps.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div>
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{c.demoEyebrow}</div><h2>{c.demoTitle}</h2></div><p>{c.demoCaption}</p></div>
      <div className="workflow-concept product-flow-live">
        <ProductExperience locale={locale} />
        <p className="workflow-concept-note">{c.demoCaption}</p>
      </div>
    </div></section>

    <section className="section surface-section"><div className="shell split-copy"><div><div className="eyebrow">{c.boundaryEyebrow}</div><h2>{c.boundaryTitle}</h2></div><div><p className="lead small">{c.boundaryText}</p></div></div></section>
  </>;
}
