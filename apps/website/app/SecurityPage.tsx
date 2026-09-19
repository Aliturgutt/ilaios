"use client";
import Link from "next/link";
import SystemVisuals from "./SystemVisuals";
import { motion } from "motion/react";

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
    report: "Report suspected vulnerabilities through security@ilaios.com. Report service misuse, spam or fraud through abuse@ilaios.com.",
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
    report: "Şüpheli güvenlik açıklarını security@ilaios.com adresine gönderin. Hizmet kötüye kullanımı, spam veya dolandırıcılık bildirimlerini abuse@ilaios.com adresine gönderin.",
  },
} as const;

export default function SecurityPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    {/* Hero Section with Motion */}
    <section className="shell page-hero compact-page-hero pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
          <h1 className="text-5xl font-bold tracking-tighter mb-4">{c.title}</h1>
        </div>
        <p className="text-base leading-relaxed max-w-2xl mt-4">{c.lead}</p>
      </motion.div>
    </section>
    <section className="section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell security-boundary-layout grid gap-8 md:grid-cols-2 items-start">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Güven sınırı" : "Trust boundary"}</div>
            <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.boundaryTitle}</h2>
            <p className="text-base leading-relaxed mb-6">{c.boundaryText}</p>
            <div className="security-detail-links flex flex-col gap-3">
              <motion.a
                key="permissions"
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
                className="text-link inline-flex items-center gap-2 text-gray-400 font-medium hover:text-black transition-colors duration-200 hover-lift hover-scale"
                href={`${base}/security/permissions`}
              >
                {c.permissions} →
              </motion.a>
              <motion.a
                key="approvals"
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
                className="text-link inline-flex items-center gap-2 text-gray-400 font-medium hover:text-black transition-colors duration-200 hover-lift hover-scale"
                href={`${base}/security/approvals`}
              >
                {c.approvals} →
              </motion.a>
              <motion.a
                key="audit"
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
                className="text-link inline-flex items-center gap-2 text-gray-400 font-medium hover:text-black transition-colors duration-200 hover-lift hover-scale"
                href={`${base}/security/audit`}
              >
                {c.audit} →
              </motion.a>
            </div>
          </div>
          <motion.div
            key="trust-gate"
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.3 } }}
            className="flex flex-col items-center gap-4 p-6 border border-text rounded-lg hover:bg-bg-lighter hover:border-text hover:text-text transition-all duration-200 hover-lift hover-scale"
          >
            <div className="dark-surface px-4 py-2 text-center">
              <span className="text-xs font-bold text-gray-400">CLIENT</span>
              <p className="text-sm font-semibold">{c.client}</p>
            </div>
            <i className="text-gray-400"><small>{c.contract}</small></i>
            <div className="is-authority dark-surface px-4 py-2 text-center">
              <span className="text-xs font-bold text-gray-400">CONTROL PLANE</span>
              <p className="text-sm font-semibold">{c.core}</p>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Talep → dış etki" : "Request → side effect"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.visualTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6">{c.visualLead}</p>
          </div>
          <SystemVisuals locale={locale} variant="trust" />
        </div>
      </motion.div>
    </section>
    <section className="section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Yürütme öncesi" : "Before execution"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.admissionTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6">{c.admissionLead}</p>
          </div>
          <div className="security-process grid gap-8">
            {c.path.map(([n, title, detail], index) => (
              <motion.div
                key={n}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="border border-text rounded-lg p-6 hover:bg-bg-lighter hover:border-text hover:text-text transition-all duration-200 hover-lift hover-scale"
              >
                <span className="text-xs font-bold text-gray-400">{n}</span>
                <strong className="text-lg font-semibold block mt-2">{title}</strong>
                <small className="text-sm text-gray-400 block mt-1">{detail}</small>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="compact-heading-row">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Güvenlik ilkeleri" : "Security principles"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.pathTitle}</h2>
            </div>
          </div>
          <div className="principle-directory grid gap-8 pt-8">
            {c.principles.map(([title, text], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="border border-text rounded-lg p-6 hover:bg-bg-lighter hover:border-text hover:text-text transition-all duration-200 hover-lift hover-scale"
              >
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold block mt-2">{title}</strong>
                <p className="text-base leading-relaxed text-gray-400 mt-1">{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell status-note text-center">
          <span className="micro-label text-xs font-bold text-gray-400">{locale === "tr" ? "Sorumlu bildirim" : "Responsible reporting"}</span>
          <p className="text-base leading-relaxed mt-2">{c.report}</p>
          <p className="mt-2">
            <motion.a
              key="security-email"
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
              className="text-link hover:text-text hover-lift hover-scale"
              href="mailto:security@ilaios.com"
            >
              security@ilaios.com
            </motion.a> ·
            <motion.a
              key="abuse-email"
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
              className="text-link hover:text-text hover-lift hover-scale"
              href="mailto:abuse@ilaios.com"
            >
              abuse@ilaios.com
            </motion.a>
          </p>
        </div>
      </motion.div>
    </section>
  </>;
}
