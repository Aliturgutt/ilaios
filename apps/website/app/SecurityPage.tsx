import Link from "next/link";
import SystemVisuals from "./SystemVisuals";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Security",
    title: "Sensitive work stays behind explicit control boundaries.",
    lead: "ILAIOS separates a request from permission to act. Identity, policy, approval, tool scope, validation and evidence determine whether consequential work can proceed.",
    boundaryTitle: "Clients request. The control plane decides.",
    boundaryText: "Web, Desktop and other clients can submit intent, show approvals and surface results. They do not become the authority source for runtime permissions or policy.",
    client: "Request · Approve · Observe",
    contract: "validated authority",
    core: "Authorize · Constrain · Verify",
    visualTitle: "A request does not become an external side effect by itself.",
    visualLead: "Models, tools, providers, browsers and workers remain execution resources. The control boundary decides what they may do and validation decides what may be accepted.",
    admissionTitle: "Before sensitive work starts, the system resolves the controls that matter.",
    admissionLead: "Identity and tenant scope, policy, required approval, allowed tools and targets, data restrictions, budget and acceptance criteria are resolved before bounded execution. Missing required authority fails closed.",
    pathTitle: "The public security model is simple: authorize, constrain, verify and retain evidence.",
    path: [["01", "Request", "Authenticated intent"], ["02", "Authorize", "Identity · policy · approval"], ["03", "Constrain", "Tools · targets · data"], ["04", "Verify", "Acceptance criteria"], ["05", "Record", "Evidence · audit context"]],
    principles: [["Least privilege", "Authority is explicit, narrow and revocable."], ["Tenant isolation", "Relevant data is not enough; access still requires the correct tenant and authorization context."], ["Human authority", "Where approval is required, it is tied to the proposed action and cannot be self-issued by an agent."], ["Fail closed", "Missing required authority, validation or evidence stops sensitive work."], ["Evidence over assertion", "Security-relevant outcomes are supported by inspectable evidence rather than trust in model narration."], ["No premature claims", "Certifications and attestations are stated only when independently obtained and current."]],
    permissions: "Permissions",
    approvals: "Approvals",
    audit: "Audit",
    report: "Report suspected vulnerabilities, service misuse, spam or fraud through the verified public route contact@ilaios.com. No separate security mailbox is presented until that public channel is verified.",
  },
  tr: {
    eyebrow: "Güvenlik",
    title: "Hassas işler açık kontrol sınırlarının arkasında kalır.",
    lead: "ILAIOS bir talep ile işlem yapma yetkisini birbirinden ayırır. Kimlik, politika, onay, araç kapsamı, doğrulama ve kanıt; önemli bir işin ilerleyip ilerleyemeyeceğini belirler.",
    boundaryTitle: "İstemciler talep eder. Kontrol katmanı karar verir.",
    boundaryText: "Web, Masaüstü ve diğer istemciler niyeti iletebilir, onayları gösterebilir ve sonuçları sunabilir. Çalışma zamanı izinleri veya politika için yetki kaynağı olmazlar.",
    client: "Talep · Onay · Gözlem",
    contract: "doğrulanmış yetki",
    core: "Yetkilendir · Sınırla · Doğrula",
    visualTitle: "Bir talep tek başına dış sistem etkisine dönüşmez.",
    visualLead: "Modeller, araçlar, sağlayıcılar, tarayıcılar ve worker'lar yürütme kaynağı olarak kalır. Ne yapabileceklerini kontrol sınırı, neyin kabul edilebileceğini ise doğrulama belirler.",
    admissionTitle: "Hassas iş başlamadan önce gerekli kontroller çözülür.",
    admissionLead: "Kimlik ve tenant kapsamı, politika, gerekli onay, izinli araç ve hedefler, veri kısıtları, bütçe ve kabul ölçütleri sınırlandırılmış yürütmeden önce belirlenir. Gerekli yetki eksikse işlem kapalı kalır.",
    pathTitle: "Kamuya açık güvenlik modeli sade: yetkilendir, sınırla, doğrula ve kanıtı koru.",
    path: [["01", "Talep", "Kimliği doğrulanmış niyet"], ["02", "Yetkilendir", "Kimlik · politika · onay"], ["03", "Sınırla", "Araçlar · hedefler · veri"], ["04", "Doğrula", "Kabul ölçütleri"], ["05", "Kaydet", "Kanıt · denetim bağlamı"]],
    principles: [["En az yetki", "Yetki açık, dar ve geri alınabilir olmalıdır."], ["Tenant izolasyonu", "Verinin ilgili olması yeterli değildir; doğru tenant ve yetki bağlamı yine gereklidir."], ["İnsan otoritesi", "Onay gerektiğinde önerilen işleme bağlanır ve bir ajan tarafından kendi kendine verilemez."], ["Kapalı kal", "Gerekli yetki, doğrulama veya kanıt eksikse hassas iş ilerlemez."], ["İddiadan önce kanıt", "Güvenlikle ilgili sonuçlar model anlatımına değil incelenebilir kanıta dayanır."], ["Erken iddia yok", "Sertifika ve doğrulamalar yalnız bağımsız olarak alınmış ve güncelse belirtilir."]],
    permissions: "İzinler",
    approvals: "Onaylar",
    audit: "Denetim",
    report: "Şüpheli güvenlik açıkları, hizmet kötüye kullanımı, spam veya dolandırıcılık bildirimleri doğrulanmış kamu kanalı contact@ilaios.com üzerinden iletilir. Ayrı bir güvenlik adresi kamuya açık kullanım için doğrulanmadan gösterilmez.",
  },
} as const;

export default function SecurityPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell security-boundary-layout"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırı" : "Trust boundary"}</div><h2>{c.boundaryTitle}</h2><p>{c.boundaryText}</p><div className="security-detail-links"><Link href={`${base}/security/permissions`}>{c.permissions} →</Link><Link href={`${base}/security/approvals`}>{c.approvals} →</Link><Link href={`${base}/security/audit`}>{c.audit} →</Link></div></div><div className="trust-gate"><div><span>CLIENT</span><strong>{c.client}</strong></div><i><small>{c.contract}</small></i><div className="is-authority"><span>CONTROL PLANE</span><strong>{c.core}</strong></div></div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Talep → dış etki" : "Request → side effect"}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div><SystemVisuals locale={locale} variant="trust" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Yürütme öncesi" : "Before execution"}</div><h2>{c.admissionTitle}</h2></div><p>{c.admissionLead}</p></div><div className="security-process">{c.path.map(([n, title, detail]) => <article key={n}><span>{n}</span><strong>{title}</strong><small>{detail}</small></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Güvenlik ilkeleri" : "Security principles"}</div><h2>{c.pathTitle}</h2></div></div><div className="principle-directory">{c.principles.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Sorumlu bildirim" : "Responsible reporting"}</span><p>{c.report}</p></div></section>
  </>;
}
