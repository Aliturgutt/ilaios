import Link from "next/link";
import { motion } from "motion/react";
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
    lead: "ILAIOS; ürün deneyimi ve yürütme kaynaklarını kimlik, politika, onaylar, durum, doğrulama, kanat ve kurtarmanın sahibi olan backend otoritesinden ayrı tutar.",
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
    <section className="shell page-hero compact-page-hero pt-16 pb-16">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
        <h1 className="text-5xl font-bold tracking-tighter mb-4">{c.title}</h1>
        <p className="text-base leading-relaxed mb-6 max-w-2xl text-gray-300">{c.lead}</p>
        <div className="actions flex items-center gap-4 mt-4">
          <Link className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href={`${base}/use-ilaios`}>
            {c.use}
          </Link>
        </div>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <div className="shell architecture-primary grid gap-8">
        <div className="max-w-2xl">
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
          >
            <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Sistem katmanları" : "System layers"}</div>
            <h2 className="text-4xl font-bold tracking-tighter mb-4">{c.flowTitle}</h2>
          </motion.div>
        </div>
        <div className="architecture-layer-list grid gap-6">
          {c.layers.map(([title, text], index) => (
            <motion.div
              key={title}
              initial={{ x: -20, opacity: 0, scale: 0.95, y: 20 }}
              whileInView={{
                x: 0,
                opacity: 1,
                scale: 1,
                y: 0,
                transition: {
                  duration: 0.6,
                  ease: [0.4, 0, 0.2, 1],
                  delay: index * 0.1
                }
              }}
            >
              <article className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold block mt-2">{title}</strong>
                <p className="text-base leading-relaxed mt-1">{text}</p>
              </article>
            </motion.div>
          ))}
        </div>
        <SpatialArchitecture locale={locale} />
      </div>
    </section>
    <section className="section surface-section pt-20 pb-20">
      <div className="shell">
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
        >
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Yönetilen yürütme" : "Governed execution"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.executionTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6">{c.executionLead}</p>
          </div>
        </motion.div>
        <SystemVisuals locale={locale} variant="execution" />
      </div>
    </section>
    <section className="section pt-20 pb-20">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="compact-heading-row">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Güven sınırları" : "Trust boundaries"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.boundariesTitle}</h2>
            </div>
          </div>
        </div>
        <div className="boundary-ledger grid gap-6 pt-8">
          {c.boundaries.map(([title, text], index) => (
            <motion.div
              key={title}
              initial={{ x: -20, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
            >
              <article className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold block mt-2">{title}</strong>
                <p className="text-base leading-relaxed mt-1">{text}</p>
              </article>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <div className="shell compact-cta text-center">
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Teknik derinlik" : "Technical depth"}</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.ctaTitle}</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <Link className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200" href={`${base}/core`}>
            {c.core}
          </Link>
          <Link className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200" href={`${base}/docs`}>
            {c.docs} →
          </Link>
        </div>
      </div>
    </section>
  </>;
}