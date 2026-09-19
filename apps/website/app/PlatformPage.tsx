import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";
import CanonicalSystemDetail from "./CanonicalSystemDetail";
import { motion } from "motion/react";

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
    assuranceEyebrow: "Technical assurance",
    assuranceTitle: "Identity, authorized context and governed knowledge remain explicit below the product flow.",
    assuranceLead: "These technical views keep request identity, authorization and source provenance inspectable without making infrastructure the primary marketing story.",
    technical: "Need the technical model?",
    architecture: "Explore architecture",
    use: "Explore what ILAIOS can produce",
    current: "ILAIOS remains under active development. Architecture direction is not a claim that every canonical capability is generally available today.",
  },
  tr: {
    eyebrow: "Ürün platformu",
    title: "Sonucu tarif et. ILAIOS işi talepten doğrulanmış teslime kadar yönetir.",
    lead: "Tek ürün sınırı; hedefi, sonucu üretmek için gereken işi, yürütmeyi yöneten kontrolleri ve sonucu kabul etmek için kullanılan kanıtı birbirine bağlar.",
    mapEyebrow: "Platform nasıl çalışır?",
    mapTitle: "İş birden fazla yeteneğe yayılsa bile kullanıcı deneyimi sade kalır.",
    planes: [["Talep", "Bir yapay zekâ araç zinciri seçip işletmek yerine ihtiyacın olan sonucu tarif ederek başla."], ["Yönet", "Kimlik, izinler, politika ve onaylar yürütmenin ne yapabileceğini belirler."], ["Üret", "Uygulanabilir sınırlandırılmış yetenekler web, yazılım, medya veya araştırma alanında kabul edilmiş işi yürütür."], ["Doğrula", "Kabul kontrolleri ve kanıt, sonucun teslime hazır olup olmadığını belirler."]],
    separationTitle: "Yürütme kaynakları değişebilir; kontrol otoritesi değişmez.",
    separationLead: "Modeller, sağlayıcılar ve araçlar yürütme kaynaklarıdır. Politika gerçeği, kiracı yetkisi ve kanıt sahipliği platformun kontrol sınırında kalır.",
    runtimeEyebrow: "Hedeften sonuca",
    runtimeTitle: "Tek kontrollü yol talebi bitmiş sonuca bağlar.",
    runtime: [["Hedef", "Sonucu tarif et"], ["Kontrol", "İzinleri çöz"], ["Plan", "İşi sınırlandır"], ["Üret", "İşi yürüt"], ["Doğrula", "Kabulü kontrol et"], ["Teslim", "Sonuç + kanıtı sun"]],
    details: [["Kontrol katmanı", "Yetkinin nasıl merkezde kaldığı", "/tr/platform/control-plane"], ["Yürütme", "Kabul edilmiş işin nasıl yapıldığı", "/tr/platform/execution"], ["Kanıt", "Sonuçların nasıl incelenebilir kaldığı", "/tr/platform/evidence"]],
    assuranceEyebrow: "Teknik güvence",
    assuranceTitle: "Kimlik, yetkili bağlam ve yönetilen bilgi ürün akışının altında açıkça korunur.",
    assuranceLead: "Bu teknik görünümler talep kimliğini, yetkilendirmeyi ve kaynak kökeni ana pazarlama anlatısına dönüştürmeden incelenebilir tutar.",
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
    {/* Hero Section with Motion */}
    <section className="shell page-hero compact-page-hero pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
        <h1 className="text-5xl font-semibold tracking-tighter mb-4">{c.title}</h1>
        <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">{c.lead}</p>
        <div className="actions flex items-center gap-4 mt-4">
          <Link className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale" href={`${base}/use-ilaios`}>
            {c.use}
          </Link>
        </div>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell platform-map-layout grid gap-8">
          <div className="platform-plane-list">
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.mapEyebrow}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.mapTitle}</h2>
            {c.planes.map(([title, text], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
              >
                <span className="text-xs font-semibold text-gray-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong className="text-lg font-semibold text-white">{title}</strong>
                  <p className="text-base leading-relaxed text-gray-300">{text}</p>
                </div>
              </motion.div>
            ))}
          </div>
          <SpatialArchitecture locale={locale} />
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
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Kontrol farkı" : "The control difference"}</div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.separationTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.separationLead}</p>
          </div>
          <SystemVisuals locale={locale} variant="planes" />
        </div>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="compact-heading-row">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.runtimeEyebrow}</div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.runtimeTitle}</h2>
            </div>
          </div>
          <div className="runtime-line grid gap-6 pt-8">
            {c.runtime.map(([title, detail], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="flex flex-col items-start gap-2"
              >
                <span className="text-xs font-semibold text-gray-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold text-white">{title}</strong>
                <small className="text-sm text-gray-400">{detail}</small>
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
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.assuranceEyebrow}</div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.assuranceTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.assuranceLead}</p>
          </div>
          <CanonicalSystemDetail locale={locale} variant="journey" />
          <CanonicalSystemDetail locale={locale} variant="knowledge" />
        </div>
      </motion.div>
    </section>
    <section className="section"><motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell detail-directory grid gap-4 pt-8">
          {c.details.map(([title, text, href], index) => (
            <motion.div
              key={href}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
              className="flex items-center gap-2 px-4 py-3 bg-gray-800 rounded-md text-base font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            >
              <span>{title}</span>
              <strong>{text}</strong>
              <i>→</i>
            </motion.div>
          ))}
        </div>
      </motion.div></section>
    <section className="section compact-section pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell compact-cta text-center">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.technical}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.separationTitle}</h2>
          </div>
          <div className="actions flex items-center justify-center gap-4 mt-8">
            <Link className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale" href={`${base}/architecture`}>
              {c.architecture}
            </Link>
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
          <span className="text-sm tracking-wider text-gray-400">{locale === "tr" ? "Güncel durum" : "Current reality"}</span>
          <p className="text-base leading-relaxed mt-2 text-gray-300">{c.current}</p>
        </div>
      </motion.div>
    </section>
  </>;
}