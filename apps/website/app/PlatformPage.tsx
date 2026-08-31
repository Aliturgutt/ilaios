import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Platform",
    title: "Describe the outcome. ILAIOS governs the work from request to verified delivery.",
    lead: "One product boundary connects the goal, the work required to produce it, the controls that govern execution and the evidence used to accept the result.",
    mapEyebrow: "How the platform works",
    mapTitle: "The experience stays simple even when the work spans multiple capabilities.",
    planes: [["Request", "Start with the result you need rather than choosing and operating a chain of AI tools."], ["Govern", "Identity, permissions, policy and approvals define what the execution is allowed to do."], ["Produce", "The applicable bounded capabilities perform the admitted work across web, software, media or research."], ["Verify", "Acceptance checks and evidence determine whether the result is ready to deliver."]],
    separationTitle: "Execution can change without moving control authority.",
    separationLead: "Models, providers and tools are execution resources. Policy truth, tenant authority and evidence ownership remain under the platform control boundary.",
    runtimeEyebrow: "From goal to result",
    runtimeTitle: "One controlled path connects the request to the finished outcome.",
    runtime: [["Goal", "Describe the outcome"], ["Control", "Resolve permissions"], ["Plan", "Bound the work"], ["Produce", "Execute the work"], ["Verify", "Check acceptance"], ["Deliver", "Return result + evidence"]],
    details: [["Control plane", "How authority stays centralized", "/platform/control-plane"], ["Execution", "How admitted work is performed", "/platform/execution"], ["Evidence", "How results remain reviewable", "/platform/evidence"]],
    technical: "Need the technical model?",
    architecture: "Explore architecture",
    use: "Explore what ILAIOS can produce",
    current: "ILAIOS remains under active development. Architecture direction is not a claim that every canonical capability is generally available today.",
  },
  tr: {
    eyebrow: "Platform",
    title: "Sonucu tarif et. ILAIOS işi talepten doğrulanmış teslime kadar yönetir.",
    lead: "Tek ürün sınırı; hedefi, sonucu üretmek için gereken işi, yürütmeyi yöneten kontrolleri ve sonucu kabul etmek için kullanılan kanıtı birbirine bağlar.",
    mapEyebrow: "Platform nasıl çalışır?",
    mapTitle: "İş birden fazla yeteneğe yayılsa bile kullanıcı deneyimi sade kalır.",
    planes: [["Talep", "Bir yapay zekâ araç zinciri seçip işletmek yerine ihtiyacın olan sonucu tarif ederek başla."], ["Yönet", "Kimlik, izinler, politika ve onaylar yürütmenin ne yapabileceğini belirler."], ["Üret", "Uygulanabilir sınırlandırılmış yetenekler web, yazılım, medya veya araştırma alanında kabul edilmiş işi yürütür."], ["Doğrula", "Kabul kontrolleri ve kanıt, sonucun teslime hazır olup olmadığını belirler."]],
    separationTitle: "Yürütme kaynakları değişebilir; kontrol otoritesi değişmez.",
    separationLead: "Modeller, sağlayıcılar ve araçlar yürütme kaynaklarıdır. Politika gerçeği, tenant yetkisi ve kanıt sahipliği platformun kontrol sınırında kalır.",
    runtimeEyebrow: "Hedeften sonuca",
    runtimeTitle: "Tek kontrollü yol talebi bitmiş sonuca bağlar.",
    runtime: [["Hedef", "Sonucu tarif et"], ["Kontrol", "İzinleri çöz"], ["Plan", "İşi sınırlandır"], ["Üret", "İşi yürüt"], ["Doğrula", "Kabulü kontrol et"], ["Teslim", "Sonuç + kanıtı sun"]],
    details: [["Kontrol katmanı", "Yetkinin nasıl merkezde kaldığı", "/tr/platform/control-plane"], ["Yürütme", "Kabul edilmiş işin nasıl yapıldığı", "/tr/platform/execution"], ["Kanıt", "Sonuçların nasıl incelenebilir kaldığı", "/tr/platform/evidence"]],
    technical: "Teknik modeli mi arıyorsun?",
    architecture: "Mimariyi incele",
    use: "ILAIOS'un neler üretebildiğini keşfet",
    current: "ILAIOS aktif geliştirme aşamasındadır. Mimari yön, her kanonik yeteneğin bugün genel kullanıma açık olduğu anlamına gelmez.",
  },
} as const;

export default function PlatformPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/use-ilaios`}>{c.use}</Link></div></section>
    <section className="section"><div className="shell platform-map-layout"><div className="platform-plane-list"><div className="eyebrow">{c.mapEyebrow}</div><h2>{c.mapTitle}</h2>{c.planes.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{text}</p></div></article>)}</div><SpatialArchitecture locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kontrol farkı" : "The control difference"}</div><h2>{c.separationTitle}</h2></div><p>{c.separationLead}</p></div><SystemVisuals locale={locale} variant="planes" /></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{c.runtimeEyebrow}</div><h2>{c.runtimeTitle}</h2></div></div><div className="runtime-line">{c.runtime.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section"><div className="shell detail-directory">{c.details.map(([title, text, href]) => <Link href={href} key={href}><span>{title}</span><strong>{text}</strong><i>→</i></Link>)}</div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{c.technical}</div><h2>{c.separationTitle}</h2></div><div className="actions"><Link className="button secondary" href={`${base}/architecture`}>{c.architecture}</Link></div></div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Güncel durum" : "Current reality"}</span><p>{c.current}</p></div></section>
  </>;
}
