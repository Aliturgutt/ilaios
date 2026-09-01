import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Architecture",
    title: "One control authority. Multiple governed ways to get work done.",
    lead: "ILAIOS keeps the product experience and execution resources separate from the backend authority that owns identity, policy, approvals, state, validation, evidence and recovery.",
    flowTitle: "The system stays understandable when each layer has one job.",
    layers: [["Experience", "Web, Desktop and API surfaces let people request work, review state and receive results."], ["Control", "Identity, permissions, policy, approvals and durable workflow state define what may happen."], ["Execution", "Factories, skills, tools and providers perform only the work admitted by the control layer."], ["Verification", "Checks and acceptance criteria decide whether produced work can advance."], ["Evidence & recovery", "Material state, provenance and bounded failure handling keep outcomes reviewable."]],
    executionTitle: "A request moves through one governed execution spine.",
    executionLead: "The system can use different capabilities or providers without turning any of them into a second authority source.",
    boundariesTitle: "Four boundaries keep capability separate from permission.",
    boundaries: [["Identity", "The request stays tied to the authenticated organizational context."], ["Authority", "Permission and required approval are resolved before consequential work proceeds."], ["Acceptance", "Generated output is not treated as finished until required checks pass."], ["Recovery", "Retry and repair remain bounded; unresolved work stops or escalates."]],
    ctaTitle: "Go deeper only where you need the technical detail.",
    use: "See what ILAIOS can produce",
    core: "Explore Core",
    docs: "Open documentation",
  },
  tr: {
    eyebrow: "Mimari",
    title: "Tek kontrol otoritesi. İşi tamamlamak için birden çok yönetilen yol.",
    lead: "ILAIOS; ürün deneyimi ve yürütme kaynaklarını kimlik, politika, onaylar, durum, doğrulama, kanıt ve kurtarmanın sahibi olan backend otoritesinden ayrı tutar.",
    flowTitle: "Her katmanın tek görevi olduğunda sistem anlaşılır kalır.",
    layers: [["Deneyim", "Web, Masaüstü ve API yüzeyleri insanların iş talep etmesini, durumu incelemesini ve sonucu almasını sağlar."], ["Kontrol", "Kimlik, izinler, politika, onaylar ve kalıcı iş akışı durumu neyin olabileceğini belirler."], ["Yürütme", "Factory'ler, skill'ler, araçlar ve sağlayıcılar yalnız kontrol katmanının kabul ettiği işi yapar."], ["Doğrulama", "Kontroller ve kabul ölçütleri üretilen işin ilerleyip ilerleyemeyeceğini belirler."], ["Kanıt ve kurtarma", "Önemli durum, kaynak kökeni ve sınırlandırılmış hata yönetimi sonuçları incelenebilir tutar."]],
    executionTitle: "Bir talep tek yönetilen yürütme omurgasından ilerler.",
    executionLead: "Sistem farklı yetenek veya sağlayıcıları kullanabilir; hiçbiri ikinci bir otorite kaynağına dönüşmez.",
    boundariesTitle: "Dört sınır, yeteneği izinden ayrı tutar.",
    boundaries: [["Kimlik", "Talep doğrulanmış organizasyon bağlamına bağlı kalır."], ["Yetki", "Önemli iş ilerlemeden önce izin ve gerekli onay çözülür."], ["Kabul", "Gerekli kontroller geçmeden üretilen çıktı bitmiş sayılmaz."], ["Kurtarma", "Yeniden deneme ve düzeltme sınırlandırılır; çözülemeyen iş durur veya yükseltilir."]],
    ctaTitle: "Teknik ayrıntıya yalnız ihtiyaç duyduğun yerde in.",
    use: "ILAIOS neler üretebilir?",
    core: "Core'u incele",
    docs: "Dokümantasyonu aç",
  },
} as const;

export default function ArchitecturePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.use}</Link></div></section>
    <section className="section"><div className="shell architecture-primary"><div><div className="eyebrow">{locale === "tr" ? "Sistem katmanları" : "System layers"}</div><h2>{c.flowTitle}</h2><div className="architecture-layer-list">{c.layers.map(([title,text],index)=><article key={title}><span>{String(index+1).padStart(2,"0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div><SpatialArchitecture locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Yönetilen yürütme" : "Governed execution"}</div><h2>{c.executionTitle}</h2></div><p>{c.executionLead}</p></div><SystemVisuals locale={locale} variant="execution" /></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırları" : "Trust boundaries"}</div><h2>{c.boundariesTitle}</h2></div></div><div className="boundary-ledger">{c.boundaries.map(([title,text],index)=><article key={title}><span>{String(index+1).padStart(2,"0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{locale === "tr" ? "Teknik derinlik" : "Technical depth"}</div><h2>{c.ctaTitle}</h2></div><div className="actions"><Link className="button secondary" href={`${base}/core`}>{c.core}</Link><Link className="text-link" href={`${base}/docs`}>{c.docs} →</Link></div></div></section>
  </>;
}
