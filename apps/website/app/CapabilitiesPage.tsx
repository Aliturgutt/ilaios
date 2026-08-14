import Link from "next/link";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Capability map",
    title: "Reusable platform capabilities are different from finished-product factories.",
    lead: "The platform provides control, context, execution and evidence primitives. Factories compose those primitives into domain outcomes.",
    columns: ["Capability", "Role", "Primary concern"],
    rows: [
      ["Governed Core", "Authority and durable state", "Policy · validation · recovery"],
      ["Identity, Tenant & Policy", "Trusted operating context", "Permissions · approvals · least authority"],
      ["Agent & Skill Runtime", "Bounded specialist execution", "Contracts · machine identity · scope"],
      ["Workflow & Recovery", "Job lifecycle", "Dependencies · retries · escalation"],
      ["Knowledge / RAG & Memory", "Cross-factory context plane", "Provenance · retrieval · grounding"],
      ["Software Intelligence", "Repository understanding", "Symbols · dependencies · typed context"],
      ["Validation & Evidence", "Acceptance control", "Checks · provenance · reviewability"],
      ["Routing & Providers", "Replaceable execution resources", "Policy-based selection · fallback boundaries"],
    ],
    factoryTitle: "Factories compose capabilities into outcomes.",
    factoryText: "Software Factory and App Factory remain separate canonical factories. Knowledge/RAG remains a shared governed plane rather than a factory.",
    factories: [["Web", "/factories/web"], ["Software", "/factories/software"], ["App", "/factories/app"], ["Video / Media", "/factories/video"], ["Security", "/factories/security"], ["Research & Data", "/factories/research-data"], ["Document", "/factories/creative-document"], ["Growth", "/factories/commerce-growth"], ["Personal Ops", "/factories/personal-operations"]],
    outcome: "Business outcome labels belong in solutions; canonical platform identities stay stable here.",
    all: "All factories",
    solutions: "Solutions",
  },
  tr: {
    eyebrow: "Yetenek haritası",
    title: "Yeniden kullanılabilir platform yetenekleri, bitmiş ürün üreten alanlarla aynı şey değildir.",
    lead: "Platform; kontrol, bağlam, yürütme ve kanıt yapı taşlarını sağlar. Üretim alanları bu yapı taşlarını alan sonuçlarına dönüştürür.",
    columns: ["Yetenek", "Rol", "Ana odak"],
    rows: [
      ["Governed Core", "Yetki ve dayanıklı durum", "Politika · doğrulama · kurtarma"],
      ["Kimlik, Tenant ve Politika", "Güvenilir çalışma bağlamı", "İzinler · onaylar · en az yetki"],
      ["Agent ve Skill Runtime", "Sınırlandırılmış uzman yürütme", "Sözleşmeler · makine kimliği · kapsam"],
      ["İş Akışı ve Kurtarma", "İş yaşam döngüsü", "Bağımlılıklar · yeniden deneme · yükseltme"],
      ["Knowledge / RAG ve Memory", "Üretim alanları arası bağlam düzlemi", "Kaynak kökeni · retrieval · grounding"],
      ["Yazılım Zekâsı", "Repository anlama", "Semboller · bağımlılıklar · typed context"],
      ["Doğrulama ve Kanıt", "Kabul kontrolü", "Kontroller · kaynak kökeni · incelenebilirlik"],
      ["Yönlendirme ve Sağlayıcılar", "Değiştirilebilir yürütme kaynakları", "Politika tabanlı seçim · fallback sınırları"],
    ],
    factoryTitle: "Üretim alanları yetenekleri sonuçlara dönüştürür.",
    factoryText: "Software Factory ve App Factory ayrı kanonik alanlar olarak kalır. Knowledge/RAG ise bir üretim alanı değil, paylaşılan yönetilen bağlam düzlemidir.",
    factories: [["Web", "/tr/factories/web"], ["Yazılım", "/tr/factories/software"], ["Uygulama", "/tr/factories/app"], ["Video / Medya", "/tr/factories/video"], ["Güvenlik", "/tr/factories/security"], ["Araştırma & Veri", "/tr/factories/research-data"], ["Doküman", "/tr/factories/creative-document"], ["Büyüme", "/tr/factories/commerce-growth"], ["Kişisel Operasyon", "/tr/factories/personal-operations"]],
    outcome: "İş sonucu etiketleri çözümler altında yer alır; kanonik platform kimlikleri burada sabit kalır.",
    all: "Tüm üretim alanları",
    solutions: "Çözümler",
  },
} as const;

export default function CapabilitiesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell"><div className="capability-matrix" role="table" aria-label={locale === "tr" ? "ILAIOS yetenek matrisi" : "ILAIOS capability matrix"}>
      <div className="capability-matrix-head" role="row">{c.columns.map(column => <strong role="columnheader" key={column}>{column}</strong>)}</div>
      {c.rows.map(([name, role, concern], index) => <div className="capability-matrix-row" role="row" key={name}><span>{String(index + 1).padStart(2, "0")}</span><strong role="cell">{name}</strong><p role="cell">{role}</p><small role="cell">{concern}</small></div>)}
    </div></div></section>
    <section className="section surface-section"><div className="shell capability-factory-band"><div><div className="eyebrow">{locale === "tr" ? "Üretim katmanı" : "Factory layer"}</div><h2>{c.factoryTitle}</h2><p>{c.factoryText}</p></div><div className="factory-link-cloud">{c.factories.map(([label, href], index) => <Link key={href} href={href}><span>{String(index + 1).padStart(2, "0")}</span>{label}</Link>)}</div></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{locale === "tr" ? "Sonuç katmanı" : "Outcome layer"}</div><h2>{c.outcome}</h2></div><div className="actions"><Link className="button" href={`${base}/factories`}>{c.all}</Link><Link className="button secondary" href={`${base}/solutions`}>{c.solutions}</Link></div></div></section>
  </>;
}
