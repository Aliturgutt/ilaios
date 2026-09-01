import Link from "next/link";

type Locale = "en" | "tr";
type FactoryStatus = "preview" | "development";
type Factory = { name: string; description: string; status: FactoryStatus; statusLabel: string; href: string; example: string };

const copy = {
  en: {
    eyebrow: "Use ILAIOS",
    title: "Describe the finished result. ILAIOS manages the path to it.",
    lead: "Start with what you want completed, add the context the work actually needs, and let ILAIOS coordinate the applicable production flow without exposing internal model or provider choreography.",
    howTitle: "A simple request can still have explicit controls.",
    howLead: "You define the outcome. ILAIOS keeps the work bounded, checks what matters and returns a result that can be reviewed.",
    steps: [["01","Describe","State the result you want finished."],["02","Add context","Provide references, documents, brand assets or constraints only when they help define the result."],["03","Plan","ILAIOS structures the work and its dependencies inside the product boundary."],["04","Produce","The applicable capabilities perform the admitted work."],["05","Verify","Required checks and approvals determine whether the result is acceptable."],["06","Receive","Accepted work is returned with the context needed to review what was delivered."]],
    createEyebrow: "What can I work toward?",
    createTitle: "Different outcomes, one governed product boundary.",
    availability: "Current availability",
    truth: "Availability labels are intentionally conservative and do not imply that every provider or release path is production-verified.",
    works: "How ILAIOS works",
    factories: "Explore production areas",
    factoryData: [
      { name: "Web", description: "New websites and site revisions moving through structure, design, implementation and QA.", status: "preview", statusLabel: "Preview", href: "/factories/web", example: "Build a premium bilingual website for my architecture studio." },
      { name: "Video / Media", description: "Reference-driven media work spanning script, assets, audio, render and validation.", status: "preview", statusLabel: "Preview", href: "/factories/video", example: "Create a 20-second launch video using these approved product images." },
      { name: "Software", description: "Repository engineering with bounded changes, tests, review and acceptance evidence.", status: "preview", statusLabel: "Preview", href: "/factories/software", example: "Implement this repository feature, run the required tests and return the review evidence." },
      { name: "Applications", description: "Application planning and bounded production work; broader mobile and Store paths remain gated separately.", status: "preview", statusLabel: "Preview", href: "/factories/app", example: "Plan and build a governed appointment application and prepare its release-readiness checklist." },
      { name: "Research & Data", description: "Source-grounded research and structured analysis with visible provenance.", status: "development", statusLabel: "In development", href: "/factories/research-data", example: "Research this market and return a source-grounded decision brief." },
      { name: "Security", description: "Authorized defensive assessment and remediation workflows.", status: "development", statusLabel: "In development", href: "/factories/security", example: "Review this authorized scope for security risks and remediation priorities." },
      { name: "Creative & Documents", description: "Controlled document composition and reviewable export paths.", status: "development", statusLabel: "In development", href: "/factories/creative-document", example: "Turn these approved source documents into a reviewable executive report." },
      { name: "Commerce & Growth", description: "Evidence-backed proposals and review-gated growth work.", status: "development", statusLabel: "In development", href: "/factories/commerce-growth", example: "Prepare a growth experiment plan from these verified performance inputs." },
      { name: "Personal Operations", description: "Repeatable personal workflows with consequential side effects governed separately.", status: "development", statusLabel: "In development", href: "/factories/personal-operations", example: "Prepare a reviewable weekly operations plan from these priorities." },
    ] as readonly Factory[],
  },
  tr: {
    eyebrow: "ILAIOS'u Kullan",
    title: "Bitmiş sonucu tarif et. ILAIOS ona giden yolu yönetsin.",
    lead: "Neyin tamamlanmasını istediğini söyle, işin gerçekten ihtiyaç duyduğu bağlamı ekle ve üretim akışını ILAIOS'un koordine etmesine bırak. İç model ve sağlayıcı koordinasyonu ürün sınırının arkasında kalır.",
    howTitle: "Basit bir talep, açık kontrollerle ilerleyebilir.",
    howLead: "Sen sonucu tanımlarsın. ILAIOS işi sınırlar, önemli kontrolleri uygular ve incelenebilir bir sonuç döndürür.",
    steps: [["01","Tarif et","Bitmesini istediğin sonucu söyle."],["02","Bağlam ekle","Sonucu tanımlamaya yardımcı olduğunda referans, doküman, marka varlığı veya kısıt ekle."],["03","Planla","ILAIOS işi ve bağımlılıklarını ürün sınırı içinde yapılandırır."],["04","Üret","Uygulanabilir yetenekler kabul edilmiş işi yürütür."],["05","Doğrula","Gerekli kontroller ve onaylar sonucun kabul edilebilir olup olmadığını belirler."],["06","Teslim al","Kabul edilen iş, neyin teslim edildiğini incelemek için gereken bağlamla birlikte sunulur."]],
    createEyebrow: "Hangi sonuçlara ilerleyebilirim?",
    createTitle: "Farklı sonuçlar, tek yönetilen ürün sınırı.",
    availability: "Güncel erişilebilirlik",
    truth: "Erişilebilirlik etiketleri bilinçli olarak ihtiyatlıdır; her sağlayıcı veya release yolunun production-verified olduğu anlamına gelmez.",
    works: "ILAIOS nasıl çalışır?",
    factories: "Üretim alanlarını keşfet",
    factoryData: [
      { name: "Web", description: "Yapı, tasarım, geliştirme ve QA üzerinden ilerleyen yeni web siteleri ve site revizyonları.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/web", example: "Mimarlık stüdyom için premium, iki dilli bir web sitesi oluştur." },
      { name: "Video / Medya", description: "Senaryo, varlık, ses, render ve doğrulamayı kapsayan referans odaklı medya çalışmaları.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/video", example: "Bu onaylı ürün görsellerini kullanarak 20 saniyelik lansman videosu oluştur." },
      { name: "Yazılım", description: "Sınırlandırılmış değişiklik, test, inceleme ve kabul kanıtı içeren repository mühendisliği.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/software", example: "Bu repository özelliğini uygula, gerekli testleri çalıştır ve inceleme kanıtını döndür." },
      { name: "Uygulamalar", description: "Uygulama planlama ve sınırlandırılmış üretim; daha geniş mobil ve Store yolları ayrı kapılar olarak kalır.", status: "preview", statusLabel: "Önizleme", href: "/tr/factories/app", example: "Kontrollü bir randevu uygulaması planla, geliştir ve release-readiness listesini hazırla." },
      { name: "Araştırma & Veri", description: "Kaynaklara dayalı araştırma ve görünür kaynak kökeniyle yapılandırılmış analiz.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/research-data", example: "Bu pazarı araştır ve kaynaklara dayalı karar özeti hazırla." },
      { name: "Güvenlik", description: "Yetkili savunma değerlendirmesi ve düzeltme iş akışları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/security", example: "Bu yetkilendirilmiş kapsamı güvenlik riskleri ve düzeltme öncelikleri için incele." },
      { name: "Yaratıcı & Doküman", description: "Kontrollü doküman oluşturma ve incelenebilir dışa aktarma yolları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/creative-document", example: "Bu onaylı kaynak dokümanlardan incelenebilir bir yönetici raporu oluştur." },
      { name: "Ticaret & Büyüme", description: "Kanıta dayalı öneriler ve inceleme kapılı büyüme çalışmaları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/commerce-growth", example: "Bu doğrulanmış performans girdilerinden bir büyüme deneyi planı hazırla." },
      { name: "Kişisel Operasyon", description: "Önemli dış etkileri ayrıca yönetilen, tekrarlanabilir kişisel iş akışları.", status: "development", statusLabel: "Geliştiriliyor", href: "/tr/factories/personal-operations", example: "Bu önceliklerden incelenebilir haftalık operasyon planı hazırla." },
    ] as readonly Factory[],
  },
} as const;

export default function UseILAIOSPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero use-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/factories`}>{c.factories}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{c.works}</Link></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.createEyebrow}</div><h2>{c.createTitle}</h2></div><p>{c.truth}</p></div><div className="use-factory-grid">{c.factoryData.map(factory => <article className="use-factory-card" key={factory.href}><div className="use-factory-card-head"><span className={`availability-chip is-${factory.status}`}>{factory.statusLabel}</span><small>{c.availability}</small></div><h3>{factory.name}</h3><p>{factory.description}</p><blockquote>{factory.example}</blockquote><Link className="text-link" href={factory.href}>{locale === "tr" ? "Ayrıntıyı aç" : "Open details"} →</Link></article>)}</div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kullanım akışı" : "Usage flow"}</div><h2>{c.howTitle}</h2></div><p>{c.howLead}</p></div><div className="use-step-grid">{c.steps.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  </>;
}
