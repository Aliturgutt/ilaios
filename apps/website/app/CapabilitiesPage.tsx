import Link from "next/link";
import CanonicalSystemDetail from "./CanonicalSystemDetail";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Capability map",
    title: "Business work and production factories share one governed capability foundation.",
    lead: "ILAIOS separates reusable platform capabilities, business operating functions and specialized production factories. The business layer composes the other two; it does not become a second runtime authority.",
    columns: ["Capability", "Role", "Primary concern"],
    rows: [
      ["Governed Core", "Authority and durable state", "Policy · validation · recovery"],
      ["Identity, Tenant & Policy", "Trusted operating context", "Permissions · approvals · least authority"],
      ["Agent & Skill Runtime", "Bounded specialist execution", "Contracts · machine identity · scope"],
      ["Workflow & Recovery", "Job lifecycle", "Dependencies · retries · escalation"],
      ["Knowledge / RAG & Memory", "Cross-factory context plane", "Provenance · authorization-aware retrieval · grounding"],
      ["Software Intelligence", "Repository understanding", "Symbols · dependencies · typed context"],
      ["Validation & Evidence", "Acceptance control", "Independent checks · provenance · reviewability"],
      ["Routing & Providers", "Replaceable execution resources", "Eligibility first · quality floor · budget-aware fallback"],
    ],
    businessTitle: "Enterprise operating functions compose governed capabilities into business work.",
    businessText: "These are workflow and intelligence families, not departments implemented as autonomous agents. Current availability must remain evidence-gated.",
    business: [["Executive intelligence", "Strategy · KPI · performance · risk"], ["Operations", "Coordination · monitoring · exceptions"], ["Finance & cost intelligence", "Cost · budget · usage · FinOps"], ["Growth & marketing", "Market intelligence · campaigns · content · measurement"], ["Commerce & sales", "Offers · proposals · controlled revenue workflows"], ["Research & data", "Grounded analysis · competitive intelligence · provenance"], ["Knowledge", "Authorized context · memory · grounded retrieval"], ["Security & governance", "Policy · approval · authorization · audit · evidence"]],
    businessStatus: "Canonical direction / In development. Finance does not imply banking/accounting authority; commerce does not imply verified CRM, payment or autonomous sales capability.",
    maturityTitle: "Capability maturity is explicit and evidence-backed.",
    maturityText: "Registration, naming or documentation does not prove production readiness. Current reality follows implementation, tests, CI, runtime and deployment evidence.",
    routingTitle: "Cost optimization never outranks security, privacy or the required quality floor.",
    routingText: "The eligible set is established first; cost, latency and reliability optimize only inside that set. If no eligible fallback fits the remaining budget, safe failure or approval/input is preferred.",
    factoryTitle: "Production factories remain specialized execution paths.",
    factoryText: "Web, Software, App, Video/Media and Document/Creative produce domain outcomes. Business functions may compose them, while Knowledge/RAG remains shared governed context rather than another factory.",
    factories: [["Web", "/factories/web"], ["Software", "/factories/software"], ["App", "/factories/app"], ["Video / Media", "/factories/video"], ["Security", "/factories/security"], ["Research & Data", "/factories/research-data"], ["Document", "/factories/creative-document"], ["Growth", "/factories/commerce-growth"], ["Personal Ops", "/factories/personal-operations"]],
    outcome: "Business goals resolve across functions, shared capabilities and factories under one evidence spine.",
    all: "All factories",
    solutions: "Solutions",
  },
  tr: {
    eyebrow: "Yetenek haritası",
    title: "Kurumsal iş akışları ve üretim alanları aynı yönetilen yetenek temelini paylaşır.",
    lead: "ILAIOS; yeniden kullanılabilir platform yeteneklerini, kurumsal çalışma fonksiyonlarını ve uzmanlaşmış üretim alanlarını ayırır. İş katmanı diğer ikisini birleştirir; ikinci bir runtime yetkisine dönüşmez.",
    columns: ["Yetenek", "Rol", "Ana odak"],
    rows: [
      ["Governed Core", "Yetki ve dayanıklı durum", "Politika · doğrulama · kurtarma"],
      ["Kimlik, Tenant ve Politika", "Güvenilir çalışma bağlamı", "İzinler · onaylar · en az yetki"],
      ["Agent ve Skill Runtime", "Sınırlandırılmış uzman yürütme", "Sözleşmeler · makine kimliği · kapsam"],
      ["İş Akışı ve Kurtarma", "İş yaşam döngüsü", "Bağımlılıklar · yeniden deneme · yükseltme"],
      ["Knowledge / RAG ve Memory", "Üretim alanları arası bağlam düzlemi", "Provenance · authorization-aware retrieval · grounding"],
      ["Yazılım Zekâsı", "Repository anlama", "Semboller · bağımlılıklar · typed context"],
      ["Doğrulama ve Kanıt", "Kabul kontrolü", "Bağımsız kontroller · provenance · incelenebilirlik"],
      ["Yönlendirme ve Sağlayıcılar", "Değiştirilebilir yürütme kaynakları", "Önce eligibility · quality floor · budget-aware fallback"],
    ],
    businessTitle: "Kurumsal çalışma fonksiyonları yönetilen yetenekleri iş sonuçlarına dönüştürür.",
    businessText: "Bunlar otonom ajanlarla temsil edilen departmanlar değil, workflow ve intelligence aileleridir. Güncel kullanılabilirlik kanıta bağlı kalır.",
    business: [["Yönetici zekâsı", "Strateji · KPI · performans · risk"], ["Operasyonlar", "Koordinasyon · izleme · istisnalar"], ["Finans ve maliyet zekâsı", "Maliyet · bütçe · kullanım · FinOps"], ["Büyüme ve pazarlama", "Pazar zekâsı · kampanyalar · içerik · ölçüm"], ["Ticaret ve satış", "Teklifler · öneriler · kontrollü gelir akışları"], ["Araştırma ve veri", "Grounded analiz · rekabet zekâsı · provenance"], ["Knowledge", "Yetkili bağlam · memory · grounded retrieval"], ["Güvenlik ve yönetişim", "Politika · onay · yetkilendirme · audit · evidence"]],
    businessStatus: "Kanonik yön / Geliştiriliyor. Finans bankacılık veya muhasebe yetkisi anlamına gelmez; ticaret doğrulanmış CRM, ödeme veya otonom satış yeteneği iddiası taşımaz.",
    maturityTitle: "Capability maturity açık ve kanıta bağlıdır.",
    maturityText: "Kayıt, isim veya dokümantasyon production readiness ispatı değildir. Current reality; implementation, test, CI, runtime ve deployment evidence ile belirlenir.",
    routingTitle: "Maliyet optimizasyonu güvenlik, gizlilik veya gerekli kalite tabanının önüne geçmez.",
    routingText: "Önce eligible küme belirlenir; cost, latency ve reliability yalnız bu kümede optimize edilir. Kalan bütçeye uyan uygun fallback yoksa safe failure veya approval/input tercih edilir.",
    factoryTitle: "Üretim alanları uzmanlaşmış yürütme yolları olarak kalır.",
    factoryText: "Web, Yazılım, Uygulama, Video/Medya ve Doküman/Kreatif alan sonuçları üretir. İş fonksiyonları bunları birleştirebilir; Knowledge/RAG ise yeni bir factory değil paylaşılan yönetilen bağlamdır.",
    factories: [["Web", "/tr/factories/web"], ["Yazılım", "/tr/factories/software"], ["Uygulama", "/tr/factories/app"], ["Video / Medya", "/tr/factories/video"], ["Güvenlik", "/tr/factories/security"], ["Araştırma & Veri", "/tr/factories/research-data"], ["Doküman", "/tr/factories/creative-document"], ["Büyüme", "/tr/factories/commerce-growth"], ["Kişisel Operasyon", "/tr/factories/personal-operations"]],
    outcome: "İş hedefleri tek kanıt omurgası altında fonksiyonlara, paylaşılan yeteneklere ve üretim alanlarına çözümlenir.",
    all: "Tüm üretim alanları",
    solutions: "Çözümler",
  },
} as const;

export default function CapabilitiesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell"><div className="capability-matrix" role="table" aria-label={locale === "tr" ? "ILAIOS yetenek matrisi" : "ILAIOS capability matrix"}><div className="capability-matrix-head" role="row">{c.columns.map(column => <strong role="columnheader" key={column}>{column}</strong>)}</div>{c.rows.map(([name, role, concern], index) => <div className="capability-matrix-row" role="row" key={name}><span>{String(index + 1).padStart(2, "0")}</span><strong role="cell">{name}</strong><p role="cell">{role}</p><small role="cell">{concern}</small></div>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kurumsal çalışma katmanı" : "Enterprise operating layer"}</div><h2>{c.businessTitle}</h2></div><p>{c.businessText}</p></div><div className="grid two-up">{c.business.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><p className="muted">{c.businessStatus}</p></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Maturity gerçeği" : "Maturity truth"}</div><h2>{c.maturityTitle}</h2></div><p>{c.maturityText}</p></div><CanonicalSystemDetail locale={locale} variant="maturity" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">FinOps + routing</div><h2>{c.routingTitle}</h2></div><p>{c.routingText}</p></div><CanonicalSystemDetail locale={locale} variant="cost" /></div></section>
    <section className="section surface-section"><div className="shell capability-factory-band"><div><div className="eyebrow">{locale === "tr" ? "Üretim katmanı" : "Factory layer"}</div><h2>{c.factoryTitle}</h2><p>{c.factoryText}</p></div><div className="factory-link-cloud">{c.factories.map(([label, href], index) => <Link key={href} href={href}><span>{String(index + 1).padStart(2, "0")}</span>{label}</Link>)}</div></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{locale === "tr" ? "Sonuç katmanı" : "Outcome layer"}</div><h2>{c.outcome}</h2></div><div className="actions"><Link className="button" href={`${base}/factories`}>{c.all}</Link><Link className="button secondary" href={`${base}/solutions`}>{c.solutions}</Link></div></div></section>
  </>;
}
