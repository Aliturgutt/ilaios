import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";
import CanonicalSystemDetail from "./CanonicalSystemDetail";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Platform",
    title: "A control-oriented platform for intelligent work.",
    lead: "ILAIOS keeps experience, authority, execution and evidence as separate responsibilities connected by durable contracts.",
    mapEyebrow: "System map",
    mapTitle: "Clients request. The control plane governs. Bounded capabilities execute.",
    planes: [["Experience", "Web, Desktop, Mobile, API, CLI and enterprise surfaces expose goals, approvals, state and delivery."], ["Control", "Identity, tenant context, policy, permissions, orchestration and authoritative state transitions."], ["Execution", "Deterministic services, tools and bounded intelligent capabilities perform admitted work."], ["Evidence", "Validation, provenance, audit context and recovery history keep consequential outcomes inspectable."]],
    separationTitle: "Control authority and execution resources remain deliberately separated.",
    separationLead: "The platform can change a model, provider or tool without moving policy truth, tenant authority or evidence ownership out of the control plane.",
    contractTitle: "Identity and authorized context are upstream contracts, not optional metadata.",
    contractText: "A request resolves principal, tenant and project context before bounded planning, capability resolution and execution admission. Downstream work cannot assume a contract that was never produced.",
    knowledgeTitle: "Knowledge is a governed cross-factory plane.",
    knowledgeText: "Authorized sources retain provenance; retrieval is filtered by principal, tenant, project and purpose before synthesis. Semantic relevance never overrides authorization.",
    runtimeEyebrow: "Runtime",
    runtimeTitle: "A request crosses explicit boundaries before it becomes an accepted result.",
    runtime: [["Goal", "Intent enters"], ["Authorize", "Policy evaluated"], ["Route", "Capability selected"], ["Execute", "Work performed"], ["Verify", "Criteria checked"], ["Deliver", "Evidence surfaced"]],
    details: [["Control plane", "Authority and durable state", "/platform/control-plane"], ["Execution", "Bounded deterministic and intelligent work", "/platform/execution"], ["Evidence", "Validation and provenance", "/platform/evidence"]],
    current: "ILAIOS remains under active development. Architecture direction is not a claim that every canonical capability is generally available today.",
  },
  tr: {
    eyebrow: "Platform",
    title: "Akıllı işler için kontrol odaklı bir platform.",
    lead: "ILAIOS; deneyim, yetki, yürütme ve kanıt sorumluluklarını dayanıklı sözleşmelerle bağlı fakat ayrı tutar.",
    mapEyebrow: "Sistem haritası",
    mapTitle: "İstemciler talep eder. Kontrol katmanı yönetir. Sınırlandırılmış yetenekler yürütür.",
    planes: [["Deneyim", "Web, Masaüstü, Mobil, API, CLI ve kurumsal yüzeyler hedef, onay, durum ve teslimi gösterir."], ["Kontrol", "Kimlik, tenant bağlamı, politika, izinler, orkestrasyon ve yetkili durum geçişleri."], ["Yürütme", "Deterministik servisler, araçlar ve sınırlandırılmış akıllı yetenekler kabul edilmiş işi yapar."], ["Kanıt", "Doğrulama, kaynak kökeni, denetim bağlamı ve kurtarma geçmişi önemli sonuçları incelenebilir tutar."]],
    separationTitle: "Kontrol yetkisi ile yürütme kaynakları bilinçli olarak ayrı tutulur.",
    separationLead: "Model, sağlayıcı veya araç değişse bile politika gerçeği, tenant yetkisi ve kanıt sahipliği kontrol katmanından çıkmaz.",
    contractTitle: "Kimlik ve yetkili bağlam, opsiyonel metadata değil upstream sözleşmelerdir.",
    contractText: "İstek; bounded planning, capability resolution ve execution admission öncesinde principal, tenant ve proje bağlamını çözer. Downstream iş üretilmemiş bir sözleşmeyi varsayamaz.",
    knowledgeTitle: "Knowledge, factory'ler arası yönetilen bir düzlemdir.",
    knowledgeText: "Yetkili kaynaklar provenance bilgisini korur; synthesis öncesinde retrieval principal, tenant, proje ve amaç üzerinden filtrelenir. Semantik benzerlik authorization'ı geçersiz kılamaz.",
    runtimeEyebrow: "Çalışma yolu",
    runtimeTitle: "Bir istek, kabul edilmiş sonuca dönüşmeden önce açık sınırları geçer.",
    runtime: [["Hedef", "Niyet girer"], ["Yetkilendir", "Politika değerlendirilir"], ["Yönlendir", "Yetenek seçilir"], ["Yürüt", "İş yapılır"], ["Doğrula", "Ölçütler kontrol edilir"], ["Teslim et", "Kanıt sunulur"]],
    details: [["Kontrol katmanı", "Yetki ve dayanıklı durum", "/tr/platform/control-plane"], ["Yürütme", "Sınırlandırılmış deterministik ve akıllı çalışma", "/tr/platform/execution"], ["Kanıt", "Doğrulama ve kaynak kökeni", "/tr/platform/evidence"]],
    current: "ILAIOS aktif geliştirme aşamasındadır. Mimari yön, her kanonik yeteneğin bugün genel kullanıma açık olduğu anlamına gelmez.",
  },
} as const;

export default function PlatformPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell platform-map-layout"><div className="platform-plane-list"><div className="eyebrow">{c.mapEyebrow}</div><h2>{c.mapTitle}</h2>{c.planes.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{text}</p></div></article>)}</div><SpatialArchitecture locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Yetki ayrımı" : "Authority separation"}</div><h2>{c.separationTitle}</h2></div><p>{c.separationLead}</p></div><SystemVisuals locale={locale} variant="planes" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Upstream sözleşmeler" : "Upstream contracts"}</div><h2>{c.contractTitle}</h2></div><p>{c.contractText}</p></div><CanonicalSystemDetail locale={locale} variant="journey" /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Knowledge / RAG</div><h2>{c.knowledgeTitle}</h2></div><p>{c.knowledgeText}</p></div><CanonicalSystemDetail locale={locale} variant="knowledge" /></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{c.runtimeEyebrow}</div><h2>{c.runtimeTitle}</h2></div></div><div className="runtime-line">{c.runtime.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section"><div className="shell detail-directory">{c.details.map(([title, text, href]) => <Link href={href} key={href}><span>{title}</span><strong>{text}</strong><i>→</i></Link>)}</div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Güncel durum" : "Current reality"}</span><p>{c.current}</p></div></section>
  </>;
}
