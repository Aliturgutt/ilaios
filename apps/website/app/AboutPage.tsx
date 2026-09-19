"use client";

import Link from "next/link";
import { motion } from "motion/react";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "About ILAIOS",
    title: "Building a governed operating system for finished digital outcomes.",
    lead: "ILAIOS is a product initiative focused on connecting authority, execution, validation, evidence and recovery in one governed operating model.",
    missionLabel: "What we are building",
    mission: "One control model coordinates the work while models, tools and providers remain replaceable execution resources rather than separate authorities.",
    principlesLabel: "Operating principles",
    principles: [["Control before convenience", "Automation stays inside explicit authority."], ["Evidence before claims", "Important outcomes remain reviewable before they are presented as accepted."], ["One authority across surfaces", "Product clients connect to the same governed backend instead of creating independent execution authority."]],
    founderLabel: "Founder",
    founder: "Ali Turgut",
    founderText: "Ali Turgut founded ILAIOS and leads its product direction, with a focus on governed automation, finished-product workflows and evidence-backed execution.",
    truthLabel: "Product truth",
    truth: "ILAIOS is under active development. Public materials separate product direction from what is currently implemented, verified, deployed and generally available.",
    solutions: "Explore outcomes",
    architecture: "Architecture",
  },
  tr: {
    eyebrow: "ILAIOS Hakkında",
    title: "Bitmiş dijital sonuçlar için yönetilen bir işletim sistemi geliştiriyoruz.",
    lead: "ILAIOS; yetki, yürütme, doğrulama, kanıt ve kurtarmayı tek yönetilen çalışma modeli içinde birleştirmeye odaklanan bir ürün girişimidir.",
    missionLabel: "Ne geliştiriyoruz?",
    mission: "Tek kontrol modeli işi koordine eder; modeller, araçlar ve sağlayıcılar ayrı otoriteler değil, değiştirilebilir yürütme kaynakları olarak kalır.",
    principlesLabel: "Çalışma ilkeleri",
    principles: [["Kolaylıktan önce kontrol", "Otomasyon açık yetki sınırları içinde kalır."], ["İddiadan önce kanıt", "Önemli sonuçlar kabul edilmiş olarak sunulmadan önce incelenebilir kalır."], ["Tüm yüzeylerde tek otorite", "Ürün istemcileri bağımsız yürütme otoritesi oluşturmak yerine aynı yönetilen arka uca bağlanır."]],
    founderLabel: "Kurucu",
    founder: "Ali Turgut",
    founderText: "Ali Turgut, ILAIOS'u kurdu ve ürün yönünü; yönetilen otomasyon, bitmiş ürün iş akışları ve kanıta dayalı yürütme odağıyla yönetiyor.",
    truthLabel: "Ürün gerçeği",
    truth: "ILAIOS aktif geliştirme aşamasındadır. Kamuya açık içerikler ürün yönünü bugün gerçekten uygulanmış, doğrulanmış, yayınlanmış ve genel kullanıma açık olan durumdan ayırır.",
    solutions: "Sonuçları keşfet",
    architecture: "Mimari",
  },
} as const;

export default function AboutPage({ locale }: { locale: Locale }) {
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
        <p className="text-base leading-relaxed max-w-2xl text-gray-300">{c.lead}</p>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell about-editorial-grid grid gap-8">
          <motion.div
            key="mission"
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4 } }}
          >
            <article className="about-mission">
              <span className="micro-label text-xs font-bold text-gray-400">{c.missionLabel}</span>
              <h2 className="text-4xl font-bold tracking-tighter mb-4">{c.mission}</h2>
            </article>
          </motion.div>
          <motion.div
            key="principles"
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
          >
            <div className="about-principles">
              <span className="micro-label text-xs font-bold text-gray-400">{c.principlesLabel}</span>
              <motion.ul
                className="grid gap-6"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
              >
                {c.principles.map(([title, text], index) => (
                  <motion.li
                    key={title}
                    initial={{ x: -10, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1, transition: { duration: 0.3, delay: index * 0.1 } }}
                    className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-xs font-bold text-gray-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <strong className="text-lg font-semibold">{title}</strong>
                        <p className="text-base leading-relaxed mt-2">{text}</p>
                      </div>
                    </div>
                  </motion.li>
                ))}
              </motion.ul>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24 bg-gray-800">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell founder-row" id="founder">
          <div className="flex flex-col items-start gap-2">
            <span className="micro-label text-xs font-bold text-gray-400">{c.founderLabel}</span>
            <h2 className="text-4xl font-bold tracking-tighter mb-2 text-white">{c.founder}</h2>
          </div>
          <p className="text-base leading-relaxed max-w-2xl text-gray-300">{c.founderText}</p>
        </div>
      </motion.div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell about-truth flex flex-col items-center gap-4 text-center">
          <div className="max-w-2xl">
            <span className="micro-label text-xs font-bold text-gray-400">{c.truthLabel}</span>
            <p className="text-base leading-relaxed mt-2 text-gray-300">{c.truth}</p>
          </div>
          <div className="actions flex flex-col md:flex-row gap-4 mt-4">
            <Link
              href={`${base}/solutions`}
              className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            >
              {c.solutions}
            </Link>
            <Link
              href={`${base}/architecture`}
              className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            >
              {c.architecture}
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  </>;
}
