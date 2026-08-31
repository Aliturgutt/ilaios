import Link from "next/link";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "What ILAIOS can do",
    title: "Research, plan, create, verify and manage work under one product boundary.",
    lead: "ILAIOS combines reusable capabilities instead of asking you to operate a different AI tool for every step.",
    capabilityTitle: "Capabilities are organized around the work you need done.",
    capabilities: [["Research", "Gather and organize source-grounded information for a goal."], ["Plan", "Turn the goal into a bounded sequence of work and dependencies."], ["Create", "Produce web, software, application, video and other digital outcomes."], ["Verify", "Apply the checks that belong to the deliverable before acceptance."], ["Automate", "Coordinate repeatable work inside explicit permissions and limits."], ["Manage", "Keep identity, approvals, project context and execution boundaries connected."], ["Measure", "Use evidence and operational signals to evaluate the result."], ["Recover", "Resume, repair or stop work safely when execution does not go as planned."]],
    exampleEyebrow: "One goal, combined capabilities",
    exampleTitle: "A product launch can move from research to production without becoming five separate workflows for the user.",
    exampleLead: "ILAIOS can coordinate the capabilities that apply while preserving one controlled execution path.",
    example: [["Research", "Understand the market and source material."], ["Plan", "Define the required deliverables and dependencies."], ["Create", "Build the website, software or media that is needed."], ["Verify", "Check each result against its applicable acceptance criteria."], ["Deliver", "Return accepted work with reviewable evidence."]],
    productionEyebrow: "Production outcomes",
    productionTitle: "Explore what those capabilities can produce.",
    factories: [["Websites", "/factories/web"], ["Software", "/factories/software"], ["Applications", "/factories/app"], ["Video", "/factories/video"], ["Research", "/factories/research-data"]],
    all: "Explore all production outcomes",
    how: "How ILAIOS works",
  },
  tr: {
    eyebrow: "ILAIOS neler yapabilir?",
    title: "Araştırma, planlama, üretim, doğrulama ve yönetimi tek ürün sınırında birleştirir.",
    lead: "ILAIOS, her adım için farklı bir yapay zekâ aracını işletmeni istemek yerine yeniden kullanılabilir yetenekleri birlikte çalıştırır.",
    capabilityTitle: "Yetenekler, bitmesini istediğin işe göre düzenlenir.",
    capabilities: [["Araştır", "Hedef için kaynak temelli bilgiyi bul ve düzenle."], ["Planla", "Hedefi sınırları ve bağımlılıkları belirli bir iş akışına dönüştür."], ["Üret", "Web, yazılım, uygulama, video ve diğer dijital sonuçları oluştur."], ["Doğrula", "Kabulden önce teslimata ait kontrolleri uygula."], ["Otomatikleştir", "Tekrarlanabilir işi açık izinlar ve sınırlar içinde koordine et."], ["Yönet", "Kimlik, onaylar, proje bağlamı ve yürütme sınırlarını birlikte tut."], ["Ölç", "Sonucu kanıt ve operasyon sinyalleriyle değerlendir."], ["Kurtar", "İş beklendiği gibi gitmediğinde güvenli biçimde devam et, düzelt veya dur." ]],
    exampleEyebrow: "Tek hedef, birleşik yetenekler",
    exampleTitle: "Bir ürün lansmanı, kullanıcı için beş ayrı iş akışına dönüşmeden araştırmadan üretime ilerleyebilir.",
    exampleLead: "ILAIOS gerekli yetenekleri aynı kontrollü yürütme yolu içinde koordine edebilir.",
    example: [["Araştır", "Pazarı ve kaynak materyali anla."], ["Planla", "Gerekli teslimatları ve bağımlılıkları belirle."], ["Üret", "Gereken web sitesi, yazılım veya medyayı oluştur."], ["Doğrula", "Her sonucu geçerli kabul ölçütleriyle kontrol et."], ["Teslim et", "Kabul edilen işi incelenebilir kanıtla sun." ]],
    productionEyebrow: "Üretim sonuçları",
    productionTitle: "Bu yeteneklerin neler üretebildiğini keşfet.",
    factories: [["Web siteleri", "/tr/factories/web"], ["Yazılım", "/tr/factories/software"], ["Uygulamalar", "/tr/factories/app"], ["Video", "/tr/factories/video"], ["Araştırma", "/tr/factories/research-data"]],
    all: "Tüm üretim sonuçlarını keşfet",
    how: "ILAIOS nasıl çalışır?",
  },
} as const;

export default function CapabilitiesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><h2>{c.capabilityTitle}</h2></div></div><div className="grid two-up">{c.capabilities.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.exampleEyebrow}</div><h2>{c.exampleTitle}</h2></div><p>{c.exampleLead}</p></div><div className="runtime-line">{c.example.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section"><div className="shell capability-factory-band"><div><div className="eyebrow">{c.productionEyebrow}</div><h2>{c.productionTitle}</h2></div><div className="factory-link-cloud">{c.factories.map(([label, href], index) => <Link key={href} href={href}><span>{String(index + 1).padStart(2, "0")}</span>{label}</Link>)}</div></div></section>
    <section className="section compact-section surface-section"><div className="shell compact-cta"><div><h2>{c.productionTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/factories`}>{c.all}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.how}</Link></div></div></section>
  </>;
}
