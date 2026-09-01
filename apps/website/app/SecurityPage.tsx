import Link from "next/link";
import SystemVisuals from "./SystemVisuals";
import CanonicalSystemDetail from "./CanonicalSystemDetail";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Security",
    title: "Security is an execution boundary, not a decorative trust page.",
    lead: "Sensitive work must cross identity, permission, approval, constraint, validation and evidence controls before it can become an accepted side effect.",
    boundaryTitle: "Clients can request. The control plane decides.",
    boundaryText: "Presentation clients surface intent and approval. They do not become the authority source for runtime policy or permissions.",
    client: "Request · Approve · Observe",
    contract: "validated contract",
    core: "Authorize · Constrain · Verify",
    visualTitle: "Authority, validation and evidence separate a request from an external side effect.",
    visualLead: "The same trust boundary applies whether the execution resource is a model, tool, provider, browser, worker or native factory step.",
    admissionTitle: "Execution admission is the security gate before routing and work.",
    admissionLead: "Authority, tenant isolation, privacy/residency, DLP/secrets, tool permission, blast radius, quality and budget are evaluated before a scoped ExecutionGrant is produced. If policy requires a human decision, approval is tied to the exact proposed action and can expire or be revoked.",
    pathTitle: "A sensitive operation has a visible control path.",
    path: [["01", "Request", "Authenticated intent"], ["02", "Authorize", "Identity · scope · approval"], ["03", "Constrain", "Tools · targets · data"], ["04", "Validate", "Acceptance criteria"], ["05", "Record", "Evidence · audit context"]],
    principles: [["Least privilege", "Authority is explicit, narrow and revocable."], ["Tenant isolation", "Another tenant's data or context is not returned merely because it is relevant."], ["Human authority", "Required approvals are exact-action scoped; agents cannot self-approve."], ["Fail closed", "Missing authority or evidence stops sensitive work."], ["Evidence over assertion", "Security outcomes require inspectable proof."], ["No premature claims", "Certifications and attestations are claimed only when actually obtained."]],
    permissions: "Permissions",
    approvals: "Approvals",
    audit: "Audit",
    report: "Report suspected vulnerabilities, service misuse, spam or fraud through the verified public route contact@ilaios.com. A dedicated security mailbox will be published only after that route is verified for public use.",
  },
  tr: {
    eyebrow: "Güvenlik",
    title: "Güvenlik, sonradan eklenen bir güven sayfası değil; yürütme sınırıdır.",
    lead: "Hassas işler kabul edilmiş bir dış etkiye dönüşmeden önce kimlik, izin, onay, kısıtlama, doğrulama ve kanıt kontrollerinden geçmelidir.",
    boundaryTitle: "İstemciler talep eder. Kontrol katmanı karar verir.",
    boundaryText: "Arayüzler niyeti ve onayı gösterir; çalışma zamanı politikası veya izinler için yetki kaynağı olmaz.",
    client: "Talep · Onay · Gözlem",
    contract: "doğrulanmış sözleşme",
    core: "Yetkilendir · Sınırla · Doğrula",
    visualTitle: "Yetki, doğrulama ve kanıt; talep ile dış sistem etkisini birbirinden ayırır.",
    visualLead: "Yürütme kaynağı model, araç, sağlayıcı, tarayıcı, worker veya yerleşik factory adımı olsa da aynı güven sınırı geçerlidir.",
    admissionTitle: "Execution admission, routing ve iş başlamadan önceki güvenlik kapısıdır.",
    admissionLead: "Scoped ExecutionGrant üretilmeden önce yetki, tenant isolation, privacy/residency, DLP/secrets, araç izni, blast radius, kalite ve bütçe değerlendirilir. Policy insan kararı gerektiriyorsa onay exact proposed action'a bağlanır; süresi dolabilir veya geri alınabilir.",
    pathTitle: "Hassas bir işlemin görünür bir kontrol yolu vardır.",
    path: [["01", "Talep", "Kimliği doğrulanmış niyet"], ["02", "Yetkilendir", "Kimlik · kapsam · onay"], ["03", "Sınırla", "Araçlar · hedefler · veri"], ["04", "Doğrula", "Kabul ölçütleri"], ["05", "Kaydet", "Kanıt · denetim bağlamı"]],
    principles: [["En az yetki", "Yetki açık, dar ve geri alınabilir olmalıdır."], ["Tenant isolation", "Başka tenant'ın verisi veya bağlamı yalnız ilgili olduğu için döndürülemez."], ["İnsan otoritesi", "Gerekli onay exact action kapsamındadır; agent kendi kendini onaylayamaz."], ["Fail closed", "Eksik yetki veya kanıt hassas işi durdurur."], ["İddiadan önce kanıt", "Güvenlik sonuçları incelenebilir kanıt gerektirir."], ["Erken iddia yok", "Sertifika ve attestation yalnız gerçekten alındığında duyurulur."]],
    permissions: "İzinler",
    approvals: "Onaylar",
    audit: "Denetim",
    report: "Şüpheli güvenlik açıklarını, hizmet kötüye kullanımını, spam veya dolandırıcılık bildirimlerini doğrulanmış kamu kanalı contact@ilaios.com üzerinden iletin. Özel güvenlik adresi yalnız kamuya açık kullanım amacı doğrulandıktan sonra yayınlanacaktır.",
  },
} as const;

export default function SecurityPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell security-boundary-layout"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırı" : "Trust boundary"}</div><h2>{c.boundaryTitle}</h2><p>{c.boundaryText}</p><div className="security-detail-links"><Link href={`${base}/security/permissions`}>{c.permissions} →</Link><Link href={`${base}/security/approvals`}>{c.approvals} →</Link><Link href={`${base}/security/audit`}>{c.audit} →</Link></div></div><div className="trust-gate"><div><span>CLIENT</span><strong>{c.client}</strong></div><i><small>{c.contract}</small></i><div className="is-authority"><span>CONTROL PLANE</span><strong>{c.core}</strong></div></div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Yetki → dış etki" : "Authority → side effect"}</div><h2>{c.visualTitle}</h2></div><p>{c.visualLead}</p></div><SystemVisuals locale={locale} variant="trust" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Execution admission + approval</div><h2>{c.admissionTitle}</h2></div><p>{c.admissionLead}</p></div><CanonicalSystemDetail locale={locale} variant="runtime" /></div></section>
    <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Hassas yürütme" : "Sensitive execution"}</div><h2>{c.pathTitle}</h2></div></div><div className="security-process">{c.path.map(([n, title, detail]) => <article key={n}><span>{n}</span><strong>{title}</strong><small>{detail}</small></article>)}</div></div></section>
    <section className="section"><div className="shell principle-directory">{c.principles.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Sorumlu bildirim" : "Responsible reporting"}</span><p>{c.report}</p></div></section>
  </>;
}
