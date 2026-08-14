import Link from "next/link";

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
    pathTitle: "A sensitive operation has a visible control path.",
    path: [["01", "Request", "Authenticated intent"], ["02", "Authorize", "Identity · scope · approval"], ["03", "Constrain", "Tools · targets · data"], ["04", "Validate", "Acceptance criteria"], ["05", "Record", "Evidence · audit context"]],
    principles: [["Least privilege", "Authority is explicit, narrow and revocable."], ["Human authority", "Required approvals are not silently delegated."], ["Fail closed", "Missing authority or evidence stops sensitive work."], ["Evidence over assertion", "Security outcomes require inspectable proof."], ["Separated authority", "Clients and models do not own policy truth."], ["No premature claims", "Certifications and attestations are claimed only when actually obtained."]],
    permissions: "Permissions",
    approvals: "Approvals",
    audit: "Audit",
    report: "Report suspected vulnerabilities to security@ilaios.com. Service misuse, spam or fraud reports go to abuse@ilaios.com.",
  },
  tr: {
    eyebrow: "Güvenlik",
    title: "Güvenlik, sonradan eklenen bir güven sayfası değil; yürütme sınırıdır.",
    lead: "Hassas işler kabul edilmiş bir yan etkiye dönüşmeden önce kimlik, izin, onay, kısıtlama, doğrulama ve kanıt kontrollerinden geçmelidir.",
    boundaryTitle: "İstemciler talep eder. Kontrol katmanı karar verir.",
    boundaryText: "Arayüzler niyeti ve onayı gösterir; çalışma zamanı politikası veya izinler için yetki kaynağı olmaz.",
    client: "Talep · Onay · Gözlem",
    contract: "doğrulanmış sözleşme",
    core: "Yetkilendir · Sınırla · Doğrula",
    pathTitle: "Hassas bir işlemin görünür bir kontrol yolu vardır.",
    path: [["01", "Talep", "Kimliği doğrulanmış niyet"], ["02", "Yetkilendir", "Kimlik · kapsam · onay"], ["03", "Sınırla", "Araçlar · hedefler · veri"], ["04", "Doğrula", "Kabul ölçütleri"], ["05", "Kaydet", "Kanıt · denetim bağlamı"]],
    principles: [["En az yetki", "Yetki açık, dar ve geri alınabilir olmalıdır."], ["İnsan otoritesi", "Gerekli onaylar sessizce devredilmez."], ["Fail closed", "Eksik yetki veya kanıt hassas işi durdurur."], ["İddiadan önce kanıt", "Güvenlik sonuçları incelenebilir kanıt gerektirir."], ["Ayrılmış yetki", "İstemciler ve modeller politika gerçeğinin sahibi olmaz."], ["Erken iddia yok", "Sertifika ve attestation yalnız gerçekten alındığında duyurulur."]],
    permissions: "İzinler",
    approvals: "Onaylar",
    audit: "Denetim",
    report: "Şüpheli güvenlik açıklarını security@ilaios.com adresine bildirin. Hizmet kötüye kullanımı, spam veya dolandırıcılık bildirimleri abuse@ilaios.com adresine gönderilmelidir.",
  },
} as const;

export default function SecurityPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell security-boundary-layout"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırı" : "Trust boundary"}</div><h2>{c.boundaryTitle}</h2><p>{c.boundaryText}</p><div className="security-detail-links"><Link href={`${base}/security/permissions`}>{c.permissions} →</Link><Link href={`${base}/security/approvals`}>{c.approvals} →</Link><Link href={`${base}/security/audit`}>{c.audit} →</Link></div></div><div className="trust-gate"><div><span>CLIENT</span><strong>{c.client}</strong></div><i><small>{c.contract}</small></i><div className="is-authority"><span>CONTROL PLANE</span><strong>{c.core}</strong></div></div></div></section>
    <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Hassas yürütme" : "Sensitive execution"}</div><h2>{c.pathTitle}</h2></div></div><div className="security-process">{c.path.map(([n, title, detail]) => <article key={n}><span>{n}</span><strong>{title}</strong><small>{detail}</small></article>)}</div></div></section>
    <section className="section"><div className="shell principle-directory">{c.principles.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Sorumlu bildirim" : "Responsible reporting"}</span><p>{c.report}</p></div></section>
  </>;
}
