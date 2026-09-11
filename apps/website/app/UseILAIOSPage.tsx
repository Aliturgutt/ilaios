import Link from "next/link";

type Locale = "en" | "tr";
type FactoryStatus = "preview" | "development";
type Factory = { name: string; description: string; status: FactoryStatus; statusLabel: string; href: string; example: string };
type Plan = { name: string; price: string; summary: string; included: readonly string[]; note: string };

const copy = {
  en: {
    eyebrow: "Use ILAIOS",
    title: "Describe the finished result. ILAIOS manages the path to it.",
    lead: "Start with what you want completed, add the context the work actually needs, and let ILAIOS coordinate the applicable production flow without exposing internal model or provider choreography.",
    howTitle: "A simple request can still have explicit controls.",
    howLead: "You define the outcome. ILAIOS keeps the work bounded, checks what matters and returns a result that can be reviewed.",
    steps: [["01","Describe","State the result you want finished."],["02","Add context","Provide references, documents, brand assets or constraints only when they help define the result."],["03","Plan","ILAIOS structures the work and its dependencies inside the product boundary."],["04","Produce","The applicable capabilities perform the admitted work."],["05","Verify","Required checks and approvals determine whether the result is acceptable."],["06","Receive","Accepted work is returned with the context needed to review what was delivered."]],
    plansEyebrow: "Plans and pricing",
    plansTitle: "Monthly plans include platform access and governed usage across all nine production areas.",
    plansLead: "Choose the level that matches your production needs. Included usage, project capacity, automation and storage increase by plan. Exceptional one-off work can use a separate quote when needed.",
    plansNote: "USD prices are launch commercial references. Final price and included usage are shown before payment. Plan availability is activated only through the applicable verified payment channel.",
    plans: [
      { name: "Free", price: "$0", summary: "Explore all nine production areas with zero-cost execution paths and bounded starter limits.", included: ["9/9 production areas", "3 active projects", "1 active automation · 30 runs/month", "2 GB storage", "Zero-cost AI paths only", "Video planning workflows included; render only when a verified zero-cost route is available"], note: "If one production-area limit is reached, other eligible areas remain available; the next step is Pro." },
      { name: "Pro", price: "$49 / month", summary: "For individual users who need premium AI/media access and higher monthly capacity.", included: ["9/9 production areas", "Premium AI and premium image access within plan limits", "20 min/month 480p-equivalent premium video starting capacity", "10 active projects", "3 active automations · 150 runs/month", "10 GB storage"], note: "Higher-cost usage consumes the plan's governed monthly capacity; the next step is Business." },
      { name: "Business", price: "$99 / month", summary: "For regular professional production with a larger shared media pool and team capacity.", included: ["9/9 production areas", "Higher premium AI and image capacity", "30 min/month Mini 480p-equivalent shared video pool", "30 active projects", "10 active automations · 500 runs/month", "50 GB storage · 3 workspace users"], note: "Faster or higher-cost media options consume the same shared plan capacity more quickly; the next step is Power." },
      { name: "Power", price: "$199 / month", summary: "For heavy professional production, larger workspaces and higher premium capacity.", included: ["9/9 production areas", "Higher premium AI and image capacity", "50 min/month Mini 480p-equivalent shared video pool", "100 active projects", "25 active automations · 2,000 runs/month", "100 GB storage · 10 workspace users"], note: "Premium model choice and quality affect how quickly the shared monthly capacity is used; Enterprise is available for larger needs." },
      { name: "Enterprise", price: "Custom quote", summary: "Contract-based capacity for organizations that need larger teams, controls, support or provider budgets.", included: ["9/9 production areas", "Contract-defined premium AI and media capacity", "Project, automation and concurrency limits defined by contract", "100 GB+ storage according to need", "Organization-sized workspace", "Contract-defined security controls, support and SLA options"], note: "Capacity and pricing are defined by the approved commercial agreement; there is no hidden automatic overage." },
    ] as readonly Plan[],
    paymentEyebrow: "How payment works",
    paymentTitle: "The customer sees the plan, included usage and final amount before payment.",
    paymentLead: "ILAIOS uses a monthly subscription model with included usage. The normal path when a plan limit is reached is an upgrade, not hidden usage billing.",
    payment: [["01","Choose a plan","Select Free, Pro, Business, Power or request an Enterprise quote."],["02","Review the final amount","The applicable currency, monthly price and included usage are presented before checkout."],["03","Verified payment activates access","A paid plan becomes active only after the payment result is verified."],["04","Use the included capacity","Monthly usage stays inside the plan's governed limits. Exceptional one-off work, when offered, uses a separate quote and explicit approval before payment."]],
    commercialEyebrow: "What customers purchase",
    commercialTitle: "Customers purchase access to ILAIOS digital production services and the finished outcomes they request.",
    commercialLead: "The product is the governed digital production service: websites, software and applications, research and documents, media and other supported production outcomes. Internal provider accounting is not the customer product.",
    commercial: [["01","Subscription access","Paid plans provide monthly access and included production capacity across the ILAIOS platform."],["02","Digital production outcomes","Customers use that capacity to request and receive supported digital work such as websites, software, applications, research, documents and media."],["03","Exceptional one-off work","When a separate high-cost job is offered outside normal included capacity, the customer receives a specific quote and must approve it before payment and execution."]],
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
    plansEyebrow: "Planlar ve fiyatlandırma",
    plansTitle: "Aylık planlar, dokuz üretim alanının tamamında platform erişimi ve plan dahil kullanım sunar.",
    plansLead: "Üretim ihtiyacına uygun planı seç. Plan yükseldikçe dahil kullanım, proje kapasitesi, otomasyon ve depolama artar. Gerektiğinde olağanüstü tek seferlik işler ayrıca tekliflendirilebilir.",
    plansNote: "TL tutarlar başlangıç ticari referansıdır; nihai TL fiyat ve dahil kullanım ödeme öncesinde gösterilir. Ücretli plan erişimi yalnız doğrulanmış ödeme sonucu ile etkinleşir.",
    plans: [
      { name: "Free", price: "0 TL/ay", summary: "Dokuz üretim alanının tamamını sıfır maliyetli yürütme yolları ve başlangıç limitleriyle deneyin.", included: ["9/9 üretim alanı", "3 aktif proje", "1 aktif otomasyon · ayda 30 çalışma", "2 GB depolama", "Yalnız uygun sıfır maliyetli AI yolları", "Ayda 10 video planlama/script/storyboard akışı; gerçek render yalnız doğrulanmış sıfır maliyetli yol varsa"], note: "Bir üretim alanının limiti dolduğunda diğer uygun alanlar çalışmaya devam eder; ana yükseltme yolu Pro'dur." },
      { name: "Pro", price: "2.401 TL/ay", summary: "Premium AI/medya erişimi ve daha yüksek aylık kapasite isteyen bireysel kullanıcılar için.", included: ["9/9 üretim alanı", "Plan limitleri içinde premium AI ve premium görsel", "Ayda 20 dk 480p eşdeğer başlangıç premium video kapasitesi", "10 aktif proje", "3 aktif otomasyon · ayda 150 çalışma", "10 GB depolama"], note: "Daha yüksek maliyetli kullanım, planın yönetilen aylık kapasitesini daha hızlı tüketir; sonraki plan Business'tır." },
      { name: "Business", price: "4.851 TL/ay", summary: "Düzenli profesyonel üretim, daha büyük ortak medya havuzu ve ekip kapasitesi için.", included: ["9/9 üretim alanı", "Pro'dan daha yüksek premium AI ve görsel kapasitesi", "Ayda 30 dk Mini 480p eşdeğer ortak video havuzu", "30 aktif proje", "10 aktif otomasyon · ayda 500 çalışma", "50 GB depolama · 3 workspace kullanıcısı"], note: "Daha hızlı veya daha yüksek maliyetli medya seçenekleri aynı ortak kapasiteyi daha hızlı tüketir; sonraki plan Power'dır." },
      { name: "Power", price: "9.751 TL/ay", summary: "Yoğun profesyonel üretim, daha büyük workspace ve yüksek premium kapasite için.", included: ["9/9 üretim alanı", "Business'tan daha yüksek premium AI ve görsel kapasitesi", "Ayda 50 dk Mini 480p eşdeğer ortak video havuzu", "100 aktif proje", "25 aktif otomasyon · ayda 2.000 çalışma", "100 GB depolama · 10 workspace kullanıcısı"], note: "Premium model ve kalite seçimi ortak aylık kapasitenin tüketim hızını etkiler; daha büyük ihtiyaçlarda Enterprise kullanılır." },
      { name: "Enterprise", price: "Sözleşmeye özel", summary: "Daha büyük ekip, kontrol, destek veya provider kapasitesi isteyen kurumlar için sözleşme bazlı plan.", included: ["9/9 üretim alanı", "Sözleşmeye özel premium AI ve medya kapasitesi", "Proje, otomasyon ve eşzamanlı iş: sözleşmeye özel", "100 GB üzeri ihtiyaca göre depolama", "Kuruma göre workspace kullanıcı sayısı", "Sözleşmeye göre güvenlik kontrolleri, destek ve SLA seçenekleri"], note: "Kapasite ve fiyat onaylı ticari sözleşmeyle belirlenir; gizli otomatik aşım ücreti yoktur." },
    ] as readonly Plan[],
    paymentEyebrow: "Ödeme nasıl çalışır?",
    paymentTitle: "Kullanıcı ödeme yapmadan önce planı, dahil kullanımı ve nihai tutarı görür.",
    paymentLead: "ILAIOS'un ana modeli aylık abonelik ve plan dahil kullanımdır. Plan limiti dolduğunda varsayılan yol gizli kullanım ücreti değil, üst plana geçiştir.",
    payment: [["01","Planı seç","Free, Pro, Business veya Power planını seç; Enterprise için özel teklif iste."],["02","Nihai tutarı gör","Ödeme öncesinde geçerli para birimi, aylık fiyat ve plan dahil kullanım açıkça gösterilir."],["03","Doğrulanmış ödeme erişimi açar","Ücretli plan yalnız ödeme sonucu doğrulandıktan sonra etkinleşir."],["04","Plan dahil kapasiteyi kullan","Aylık kullanım plan limitleri içinde ilerler. Sunulması halinde olağanüstü tek seferlik işler ayrı teklif ve açık kullanıcı onayıyla ödeme öncesinde netleştirilir."]],
    commercialEyebrow: "Kullanıcı ne satın alır?",
    commercialTitle: "Kullanıcı ILAIOS dijital üretim hizmetlerine erişim ve talep ettiği bitmiş dijital sonuçları satın alır.",
    commercialLead: "Satılan ürün; yönetilen dijital üretim hizmetidir: web siteleri, yazılım ve uygulama işleri, araştırma ve dokümanlar, medya ve desteklenen diğer üretim sonuçları. İç sağlayıcı muhasebesi müşteri ürünü değildir.",
    commercial: [["01","Abonelik erişimi","Ücretli planlar ILAIOS platformuna aylık erişim ve plan dahil üretim kapasitesi sağlar."],["02","Dijital üretim sonuçları","Kullanıcı bu kapasiteyle web sitesi, yazılım, uygulama, araştırma, doküman, medya ve desteklenen diğer dijital işleri talep edip teslim alır."],["03","Olağanüstü tek seferlik iş","Normal plan kapasitesi dışında ayrı yüksek maliyetli bir iş sunulursa kullanıcıya özel teklif gösterilir; ödeme ve yürütme öncesinde açık onay gerekir."]],
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
    <section className="section surface-section" id="plans"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.plansEyebrow}</div><h2>{c.plansTitle}</h2></div><p>{c.plansLead}</p></div><div className="use-factory-grid">{c.plans.map(plan => <article className="use-factory-card dark-surface" key={plan.name}><div className="use-factory-card-head"><span className="availability-chip is-preview">{plan.price}</span><small>{plan.name}</small></div><h3>{plan.name}</h3><p>{plan.summary}</p><ul>{plan.included.map(item => <li key={item}>{item}</li>)}</ul><small>{plan.note}</small></article>)}</div><p className="lead">{c.plansNote}</p></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.paymentEyebrow}</div><h2>{c.paymentTitle}</h2></div><p>{c.paymentLead}</p></div><div className="use-step-grid">{c.payment.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.createEyebrow}</div><h2>{c.createTitle}</h2></div><p>{c.truth}</p></div><div className="use-factory-grid">{c.factoryData.map(factory => <article className="use-factory-card dark-surface" key={factory.href}><div className="use-factory-card-head"><span className={`availability-chip is-${factory.status}`}>{factory.statusLabel}</span><small>{c.availability}</small></div><h3>{factory.name}</h3><p>{factory.description}</p><blockquote>{factory.example}</blockquote><Link className="text-link" href={factory.href}>{locale === "tr" ? "Ayrıntıyı aç" : "Open details"} →</Link></article>)}</div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kullanım akışı" : "Usage flow"}</div><h2>{c.howTitle}</h2></div><p>{c.howLead}</p></div><div className="use-step-grid">{c.steps.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.commercialEyebrow}</div><h2>{c.commercialTitle}</h2></div><p>{c.commercialLead}</p></div><div className="use-step-grid">{c.commercial.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  </>;
}
