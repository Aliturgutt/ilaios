"use client";
import Link from "next/link";
import CanonicalSystemDetail from "./CanonicalSystemDetail";
import { motion } from "motion/react";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "What ILAIOS can do",
    title: "Research, plan, create, verify and manage work under one product boundary.",
    lead: "ILAIOS combines reusable capabilities instead of asking you to operate a different AI tool for every step.",
    capabilityTitle: "Capabilities are organized around the work you need done.",
    capabilities: [["Research", "Gather and organize source-grounded information for a goal."], ["Plan", "Turn the goal into a bounded sequence of work and dependencies."], ["Create", "Produce web, software, application, video and other digital outcomes."], ["Verify", "Apply the checks that belong to the deliverable before acceptance."], ["Automate", "Coordinate repeatable work inside explicit permissions and limits."], ["Manage", "Keep identity, approvals, project context and execution boundaries connected."], ["Measure", "Use evidence and operational signals to evaluate the result."], ["Recover", "Resume, repair or stop work safely when execution does not go as planned."]],
    exampleEyebrow: "One goal, combined capabilities",
    exampleTitle: "A product launch can move from research to production without becoming five separate workflows for the user.",
    exampleLead: "ILAIOS can coordinate the capabilities that apply while preserving one controlled execution path.",
    example: [["Research", "Understand the market and source material."], ["Plan", "Define the required deliverables and dependencies."], ["Create", "Build the website, software or media that is needed."], ["Verify", "Check each result against its applicable acceptance criteria."], ["Deliver", "Return accepted work with reviewable evidence."]],
    productionEyebrow: "Production outcomes",
    productionTitle: "Explore what those capabilities can produce.",
    truthEyebrow: "Evidence before claims",
    truthTitle: "Capability status and cost choices remain evidence-bound.",
    truthLead: "The detailed maturity and cost-control model is kept here as technical assurance, while the main page stays focused on what users can accomplish.",
    factories: [["Websites", "/factories/web"], ["Video / Media", "/factories/video"], ["Software", "/factories/software"], ["Applications", "/factories/app"], ["Research & Data", "/factories/research-data"], ["Security", "/factories/security"], ["Documents", "/factories/creative-document"], ["Growth", "/factories/commerce-growth"], ["Personal Operations", "/factories/personal-operations"]],
    all: "Explore all production outcomes",
    how: "How ILAIOS works",
  },
  tr: {
    eyebrow: "ILAIOS neler yapabilir?",
    title: "Araştırma, planlama, üretim, doğrulama ve yönetimi tek ürün sınırında birleştirir.",
    lead: "ILAIOS, her adım için farklı bir yapay zekâ aracını işletmeni istemek yerine yeniden kullanılabilir yetenekleri birlikte çalıştırır.",
    capabilityTitle: "Yetenekler, bitmesini istediğin işe göre düzenlenir.",
    capabilities: [["Araştır", "Hedef için kaynak temelli bilgiyi bul ve düzenle."], ["Planla", "Hedefi sınırları ve bağımlılıkları belirli bir iş akışına dönüştür."], ["Üret", "Web, yazılım, uygulama, video ve diğer dijital sonuçları oluştur."], ["Doğrula", "Kabulden önce teslimata ait kontrolleri uygula."], ["Otomatikleştir", "Tekrarlanabilir işi açık izinler ve sınırlar içinde koordine et."], ["Yönet", "Kimlik, onaylar, proje bağlamı ve yürütme sınırlarını birlikte tut."], ["Ölç", "Sonucu kanıt ve operasyon sinyalleriyle değerlendir."], ["Kurtar", "İş beklendiği gibi gitmediğinde güvenli biçimde devam et, düzelt veya dur." ]],
    exampleEyebrow: "Tek hedef, birleşik yetenekler",
    exampleTitle: "Bir ürün lansmanı, kullanıcı için beş ayrı iş akışına dönüşmeden araştırmadan üretime ilerleyebilir.",
    exampleLead: "ILAIOS gerekli yetenekleri aynı controllü yürütme yolu içinde koordine edebilir.",
    example: [["Araştır", "Pazarı ve kaynak materyali anla."], ["Planla", "Gerekli teslimatları ve bağımlılıkları belirle."], ["Üret", "Gereken web sitesi, yazılım veya medyayı oluştur."], ["Doğrula", "Her sonucu geçerli kabul ölçütleriyle kontrol et."], ["Teslim et", "Kabul edilen işi incelenebilir kanıtla sun." ]],
    productionEyebrow: "Üretim sonuçları",
    productionTitle: "Bu yeteneklerin neler üretebildiğini keşfet.",
    truthEyebrow: "İddiadan önce kanıt",
    truthTitle: "Yetenek durumu ve maliyet seçimleri kanıta bağlı kalır.",
    truthLead: "Ayrıntılı olgunluk ve maliyet kontrol modeli teknik güvence olarak burada tutulur; ana sayfa ise kullanıcının elde edeceği sonuca odaklanır.",
    factories: [["Web siteleri", "/tr/factories/web"], ["Video / Medya", "/tr/factories/video"], ["Yazılım", "/tr/factories/software"], ["Uygulamalar", "/tr/factories/app"], ["Araştırma & Veri", "/tr/factories/research-data"], ["Güvenlik", "/tr/factories/security"], ["Doküman", "/tr/factories/creative-document"], ["Büyüme", "/tr/factories/commerce-growth"], ["Kişisel Operasyon", "/tr/factories/personal-operations"]],
    all: "Tüm üretim sonuçlarını keşfet",
    how: "ILAIOS nasıl çalışır?",
  },
} as const;

export default function CapabilitiesPage({ locale }: { locale: Locale }) {
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
        <h1 className="text-5xl font-bold tracking-tighter mb-4">{c.title}</h1>
        <p className="text-base leading-relaxed max-w-2xl mb-6">{c.lead}</p>
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
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.capabilityTitle}</h2>
            </div>
          </div>
          <div className="grid two-up capability-matrix gap-6 pt-8">
            {c.capabilities.map(([title, text], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
              >
                <h3 className="text-lg font-semibold mb-2">{title}</h3>
                <p className="text-base leading-relaxed">{text}</p>
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
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.exampleEyebrow}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.exampleTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6">{c.exampleLead}</p>
          </div>
          <div className="runtime-line grid gap-6 pt-8">
            {c.example.map(([title, detail], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="flex flex-col items-start gap-2"
              >
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                <strong className="text-lg font-semibold text-white">{title}</strong>
                <small className="text-sm text-gray-400">{detail}</small>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section"><motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell capability-factory-band pt-16 pb-16">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.productionEyebrow}</div>
            <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.productionTitle}</h2>
          </div>
          <div className="factory-link-cloud flex flex-wrap gap-4 pt-4">
            {c.factories.map(([label, href], index) => (
              <motion.div
                key={href}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-md text-sm font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
              >
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                {label}
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div></section>
    <section className="section surface-section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <div className="eyebrow text-sm tracking-wider text-gray-400">{c.truthEyebrow}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.truthTitle}</h2>
            </div>
            <p className="text-base leading-relaxed mb-6">{c.truthLead}</p>
          </div>
          <CanonicalSystemDetail locale={locale} variant="maturity" />
          <CanonicalSystemDetail locale={locale} variant="cost" />
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
            <h2 className="text-3xl font-bold tracking-tighter mb-4">{c.productionTitle}</h2>
          </div>
          <div className="actions flex items-center justify-center gap-4 mt-8">
            <Link className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale" href={`${base}/factories`}>
              {c.all}
            </Link>
            <Link className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale" href={`${base}/how-it-works`}>
              {c.how}
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  </>;
}
