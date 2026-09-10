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
    plansTitle: "Monthly plans provide platform access and included digital production capacity across all nine production areas.",
    plansLead: "ILAIOS uses a monthly subscription model. Included capacity is governed by the selected plan; when a plan limit is reached, the normal customer path is to upgrade rather than receive automatic extra charges.",
    plansNote: "USD plan references are canonical. Turkish paid-plan amounts are not shown here until a canonical TL price is configured; the final applicable amount must be presented before checkout. This page does not present an inactive payment channel as active.",
    plans: [
      { name: "Free", price: "$0", summary: "Starter access across all nine production areas using only verified zero-cost AI/provider routes.", included: ["9/9 production areas", "3 active projects", "1 active automation · 30 runs/month", "2 GB storage", "1 concurrent job", "Video render only through a verified $0 provider/model route; no fixed paid-video minutes or resolution"], note: "If a Free limit is reached, the upgrade path is Pro." },
      { name: "Pro", price: "$49 / month", summary: "Paid plan with governed provider access and the first shared premium-video allowance.", included: ["Includes the Free plan scope", "Seedance 2.0 Mini", "20 min/month shared Mini 480p-equivalent video pool", "Maximum plan video quality: 480p", "1 concurrent job"], note: "Higher-cost model or quality choices consume the same shared allowance faster. The next plan is Business." },
      { name: "Business", price: "$99 / month", summary: "Professional plan with a larger shared video pool and higher video quality ceiling.", included: ["Includes Pro + Free scope", "Seedance 2.0 Mini + Seedance 2.0 Fast", "30 min/month shared Mini 480p-equivalent video pool", "Maximum plan video quality: 720p", "1 concurrent job"], note: "The 30 minutes are one shared pool, not separate model quotas. The next plan is Power." },
      { name: "Power", price: "$199 / month", summary: "Higher-capacity plan with the broadest standard video model set.", included: ["Includes Business + Pro + Free scope", "Seedance 2.0 Mini + Fast + Seedance 2.0", "50 min/month shared Mini 480p-equivalent video pool", "Maximum plan video quality: 1080p", "1 concurrent job"], note: "The 50 minutes are a shared equivalent pool; 1080p is the plan ceiling, not a promise of 50 minutes at 1080p." },
      { name: "Enterprise", price: "Custom contract", summary: "Contract-specific capacity based on the Power plan foundation.", included: ["Includes the Power plan foundation", "Power video models + contract-allowlisted models", "Contract-specific video budget and capacity", "Maximum plan video quality: 4K", "Provider support and commercial policy still apply"], note: "Enterprise capacity and pricing are defined by contract; there is no hidden automatic overage." },
    ] as readonly Plan[],
    paymentEyebrow: "Subscription model",
    paymentTitle: "Customers buy monthly access to ILAIOS and the digital production capacity included in their plan.",
    paymentLead: "ILAIOS does not sell customer token packs or routine per-job credits. Plan limits do not trigger surprise invoices or automatic overage charges.",
    payment: [["01","Choose a plan","Choose Free, Pro, Business or Power; Enterprise is contract-specific."],["02","Review plan scope","See the monthly price, included capacity and relevant limits before checkout."],["03","Verified payment is required","When paid checkout is available, paid access is activated only after the payment result is verified."],["04","Use included capacity","Work stays inside the selected plan. When a normal plan limit is reached, upgrade to a higher plan for more capacity."]],
    commercialEyebrow: "What customers purchase",
    commercialTitle: "ILAIOS sells digital software-platform access and included digital production capacity, not physical goods.",
    commercialLead: "Customers use ILAIOS through app.ilaios.com and ILAIOS Desktop for supported web, software, application, research, document, video and other digital production workflows. www.ilaios.com provides corporate, product, plan and pricing information.",
    commercial: [["01","Subscription access","Paid plans provide monthly access to the ILAIOS software platform and plan-included capacity."],["02","Digital services","Customers use that capacity for supported AI/media/factory workflows and digital production outcomes."],["03","No physical products","ILAIOS does not sell or ship physical goods; supported services are delivered digitally through the product applications."]],
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
    plansTitle: "Aylık planlar, dokuz üretim alanının tamamında platform erişimi ve plana dahil dijital üretim kapasitesi sunar.",
    plansLead: "ILAIOS'un müşteri modeli aylık aboneliktir. Kullanım seçilen planın sınırları içinde ilerler; plan limiti dolduğunda otomatik ek ücret yerine normal yol üst plana geçmektir.",
    plansNote: "Ücretli planların kesin TL satış fiyatı için canonical authority henüz yapılandırılmadığından tahmini TL tutarı gösterilmez. Nihai geçerli tutar ödeme öncesinde gösterilmelidir. Bu sayfa henüz aktif olmayan bir ödeme kanalını aktifmiş gibi sunmaz.",
    plans: [
      { name: "Free", price: "0 TL", summary: "Dokuz üretim alanının tamamında yalnız doğrulanmış sıfır maliyetli AI/provider yollarıyla başlangıç erişimi.", included: ["9/9 üretim alanı", "3 aktif proje", "1 aktif otomasyon · ayda 30 çalışma", "2 GB depolama", "1 eşzamanlı iş", "Video render yalnız doğrulanmış $0 provider/model yolu varsa; sabit ücretli video dakikası veya çözünürlük vaadi yok"], note: "Free limiti dolarsa yükseltme yolu Pro'dur." },
      { name: "Pro", price: "TL fiyatı ödeme öncesinde gösterilir", summary: "Yönetilen ücretli provider erişimi ve ilk ortak premium-video hakkını içeren plan.", included: ["Free plan kapsamını içerir", "Seedance 2.0 Mini", "Ayda 20 dk ortak Mini 480p-eşdeğer video havuzu", "Maksimum plan video kalitesi: 480p", "1 eşzamanlı iş"], note: "Daha yüksek maliyetli model veya kalite aynı ortak havuzu daha hızlı tüketir. Sonraki plan Business'tır." },
      { name: "Business", price: "TL fiyatı ödeme öncesinde gösterilir", summary: "Daha büyük ortak video havuzu ve daha yüksek video kalite tavanı sunan profesyonel plan.", included: ["Pro + Free kapsamını içerir", "Seedance 2.0 Mini + Seedance 2.0 Fast", "Ayda 30 dk ortak Mini 480p-eşdeğer video havuzu", "Maksimum plan video kalitesi: 720p", "1 eşzamanlı iş"], note: "30 dakika ayrı model kotaları değil, tek ortak havuzdur. Sonraki plan Power'dır." },
      { name: "Power", price: "TL fiyatı ödeme öncesinde gösterilir", summary: "Standart planlar içindeki en geniş video model seti ve daha yüksek ortak kapasite.", included: ["Business + Pro + Free kapsamını içerir", "Seedance 2.0 Mini + Fast + Seedance 2.0", "Ayda 50 dk ortak Mini 480p-eşdeğer video havuzu", "Maksimum plan video kalitesi: 1080p", "1 eşzamanlı iş"], note: "50 dakika ortak eşdeğer havuzdur; 1080p plan tavanıdır, 50 dakika 1080p vaadi değildir." },
      { name: "Enterprise", price: "Özel sözleşme", summary: "Power plan temelini kullanan, kapasitesi sözleşmeye göre belirlenen kurumsal plan.", included: ["Power plan temelini içerir", "Power video modelleri + sözleşmeyle allowlist edilen modeller", "Sözleşmeye özel video budget/capacity", "Maksimum plan video kalitesi: 4K", "Provider desteği ve commercial policy şarttır"], note: "Enterprise kapasitesi ve fiyatı sözleşmeyle belirlenir; gizli otomatik aşım ücreti yoktur." },
    ] as readonly Plan[],
    paymentEyebrow: "Abonelik modeli",
    paymentTitle: "Kullanıcı aylık ILAIOS erişimini ve planına dahil dijital üretim kapasitesini satın alır.",
    paymentLead: "ILAIOS müşteri token paketi, kredi paketi veya rutin işlem başına ücret satmaz. Plan limiti dolduğunda sürpriz fatura ya da otomatik ek tahsilat oluşmaz.",
    payment: [["01","Planı seç","Free, Pro, Business veya Power planını seç; Enterprise sözleşmeye özeldir."],["02","Plan kapsamını gör","Ödeme öncesinde aylık fiyat, dahil kapasite ve ilgili plan sınırları gösterilir."],["03","Doğrulanmış ödeme gerekir","Ücretli checkout kullanıma açıldığında ücretli erişim yalnız ödeme sonucu doğrulandıktan sonra etkinleştirilir."],["04","Plan dahil kapasiteyi kullan","Kullanım seçilen plan içinde ilerler. Normal plan limiti dolduğunda daha yüksek kapasite için üst plana geçilir."]],
    commercialEyebrow: "Kullanıcı ne satın alır?",
    commercialTitle: "ILAIOS fiziksel ürün değil; yazılım platformu erişimi ve plana dahil dijital üretim kapasitesi satar.",
    commercialLead: "Kullanıcılar web, yazılım, uygulama, araştırma, doküman, video ve diğer desteklenen dijital üretim süreçlerini app.ilaios.com ve ILAIOS Desktop üzerinden kullanır. www.ilaios.com kurumsal, ürün, plan ve fiyatlandırma bilgisini sunar.",
    commercial: [["01","Abonelik erişimi","Ücretli planlar ILAIOS yazılım platformuna aylık erişim ve plana dahil kapasite sağlar."],["02","Dijital hizmetler","Kullanıcı bu kapasiteyi desteklenen AI/media/factory akışları ve dijital üretim sonuçları için kullanır."],["03","Fiziksel ürün yok","ILAIOS fiziksel ürün satmaz veya göndermez; desteklenen hizmetler ürün uygulamaları üzerinden dijital olarak sunulur."]],
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
    <section className="section surface-section" id="plans"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.plansEyebrow}</div><h2>{c.plansTitle}</h2></div><p>{c.plansLead}</p></div><div className="use-factory-grid">{c.plans.map(plan => <article className="use-factory-card" key={plan.name}><div className="use-factory-card-head"><span className="availability-chip is-preview">{plan.price}</span><small>{plan.name}</small></div><h3>{plan.name}</h3><p>{plan.summary}</p><ul>{plan.included.map(item => <li key={item}>{item}</li>)}</ul><small>{plan.note}</small></article>)}</div><p className="lead">{c.plansNote}</p></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.paymentEyebrow}</div><h2>{c.paymentTitle}</h2></div><p>{c.paymentLead}</p></div><div className="use-step-grid">{c.payment.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.createEyebrow}</div><h2>{c.createTitle}</h2></div><p>{c.truth}</p></div><div className="use-factory-grid">{c.factoryData.map(factory => <article className="use-factory-card" key={factory.href}><div className="use-factory-card-head"><span className={`availability-chip is-${factory.status}`}>{factory.statusLabel}</span><small>{c.availability}</small></div><h3>{factory.name}</h3><p>{factory.description}</p><blockquote>{factory.example}</blockquote><Link className="text-link" href={factory.href}>{locale === "tr" ? "Ayrıntıyı aç" : "Open details"} →</Link></article>)}</div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kullanım akışı" : "Usage flow"}</div><h2>{c.howTitle}</h2></div><p>{c.howLead}</p></div><div className="use-step-grid">{c.steps.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{c.commercialEyebrow}</div><h2>{c.commercialTitle}</h2></div><p>{c.commercialLead}</p></div><div className="use-step-grid">{c.commercial.map(([n,title,text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  </>;
}
