import Link from "next/link";
import CanonicalSystemDetail from "./CanonicalSystemDetail";
import FactoryExplorer from "./FactoryExplorer";
import { motion } from "motion/react";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Production outcomes",
    title: "Create different kinds of finished work from one goal.",
    lead: "Websites, video, software, applications and research are different outcomes, but you should not have to operate them as separate AI products.",
    visualEyebrow: "One goal, the right production path",
    visualTitle: "ILAIOS coordinates the work needed for the outcome.",
    visualLead: "A request can use one or more production areas while the user stays focused on the result rather than provider, model or tool configuration.",
    combineEyebrow: "Cross-factory composition",
    combineTitle: "A single launch can require more than one kind of work.",
    combineLead: "For example, a product launch may require research, a website, software changes and media. ILAIOS is designed to coordinate the relevant work under the same control model.",
    combine: [["Research", "Understand the market and source material."], ["Website", "Create the customer-facing product surface."], ["Software / App", "Implement the bounded product work that is needed."], ["Video", "Create supporting media from approved material."], ["Verify", "Apply the checks that belong to each deliverable."]],
    sharedEyebrow: "Shared project context",
    sharedTitle: "Production areas can use the same authorized project knowledge.",
    sharedLead: "That keeps context consistent across deliverables without turning project knowledge into another product surface or a separate authority.",
    assuranceTitle: "Shared knowledge remains governed context, not another production authority.",
    assuranceLead: "The technical assurance view below keeps authorization and provenance boundaries explicit without putting infrastructure jargon in the primary marketing flow.",
    closeTitle: "Choose the outcome you want to explore.",
    closePrimary: "See all capabilities",
    closeSecondary: "How ILAIOS works",
  },
  tr: {
    eyebrow: "Üretim sonuçları",
    title: "Tek bir hedeften farklı türde bitmiş işler üret.",
    lead: "Web sitesi, video, yazılım, uygulama ve araştırma farklı sonuçlardır; ancak bunları ayrı ayrı yapay zekâ ürünleri gibi işletmek zorunda olmamalısın.",
    visualEyebrow: "Tek hedef, doğru üretim yolu",
    visualTitle: "ILAIOS sonuç için gereken işi koordine eder.",
    visualLead: "Bir istek bir veya birden fazla üretim alanını kullanabilir; kullanıcı sağlayıcı, model veya araç ayarı yerine sonuca odaklanır.",
    combineEyebrow: "Üretim alanları arası bileşim",
    combineTitle: "Tek bir lansman birden fazla iş türü gerektirebilir.",
    combineLead: "Örneğin bir ürün lansmanı araştırma, web sitesi, yazılım değişiklikleri ve medya gerektirebilir. ILAIOS ilgili işi aynı kontrol modeli altında koordine etmek üzere tasarlanmıştır.",
    combine: [["Araştırma", "Pazarı ve kaynak materyali anla."], ["Web sitesi", "Müşteriye açık ürün yüzeyini oluştur."], ["Yazılım / Uygulama", "Gereken sınırları belirli ürün işini uygula."], ["Video", "Onaylı materyalden destekleyici medya üret."], ["Doğrula", "Her teslimata ait kontrolleri uygula."]],
    sharedEyebrow: "Paylaşılan proje bağlamı",
    sharedTitle: "Üretim alanları aynı yetkili proje bilgisinden yararlanabilir.",
    sharedLead: "Bu, proje bilgisini ayrı bir ürün yüzeyine veya ikinci bir otoriteye dönüştürmeden teslimatlar arasındaki bağlamı tutarlı tutar.",
    assuranceTitle: "Paylaşılan bilgi, yeni bir üretim yetkisi değil yönetilen bağlam olarak kalır.",
    assuranceLead: "Aşağıdaki teknik güvence görünümü, ana pazarlama akışını altyapı jargonuyla doldurmadan yetki ve kaynak kökeni sınırlarını açık tutar.",
    closeTitle: "Keşfetmek istediğin sonucu seç.",
    closePrimary: "Tüm yetenekleri gör",
    closeSecondary: "ILAIOS nasıl çalışır?",
  },
} as const;

export default function FactoriesPage({ locale }: { locale: Locale }) {
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
        <h1 className="text-5xl font-semibold tracking-tighter mb-4 text-white">{c.title}</h1>
        <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">{c.lead}</p>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24 bg-gray-800">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.visualEyebrow}</div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">{c.visualTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.visualLead}</p>
          </div>
          <FactoryExplorer locale={locale} />
        </div>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.combineEyebrow}</div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">{c.combineTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.combineLead}</p>
          </div>
          <div className="runtime-line grid gap-6 pt-8">
            {c.combine.map(([title, detail], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="flex flex-col items-start gap-2"
              >
                <span className="text-xs font-semibold text-gray-500 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold text-white">{title}</strong>
                <small className="text-sm text-gray-500">{detail}</small>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section factory-shared-context pt-10 pb-10">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="architecture-story-copy" style={{ maxWidth: "760px" }}>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.sharedEyebrow}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">{c.sharedTitle}</h2>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.sharedLead}</p>
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24 bg-gray-800">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">{c.assuranceTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6 text-gray-300">{c.assuranceLead}</p>
          </div>
          <CanonicalSystemDetail locale={locale} variant="knowledge" />
        </div>
      </motion.div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell compact-cta text-center">
          <div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">{c.closeTitle}</h2>
          </div>
          <div className="actions flex items-center justify-center gap-4 mt-8">
            <Link className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale" href={`${base}/capabilities`}>
              {c.closePrimary}
            </Link>
            <Link className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale" href={`${base}/how-it-works`}>
              {c.closeSecondary}
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  </>;
}