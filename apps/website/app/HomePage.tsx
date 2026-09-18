"use client";

import Link from "next/link";
import Image from "next/image";
import GovernanceEvidence from "./GovernanceEvidence";
import ProductExperience from "./ProductExperience";
import { motion, AnimatePresence } from "motion/react";
import { useState, useEffect, useRef } from "react";

type Locale = "en" | "tr";
type Audience = "enterprise" | "individuals";

const copy = {
  en: {
    eyebrow: "From goal to finished result",
    title: "Describe what you need. ILAIOS manages the work to a verified result.",
    lead: "Start with one clear outcome. ILAIOS coordinates the work, applies the controls that matter, checks the result and keeps the evidence with the delivery.",
    primary: "See what ILAIOS can create",
    secondary: "How it works",
    proof: [["One goal", "Start with the outcome, not a stack of tools."], ["Managed execution", "Work stays inside explicit permissions and controls."], ["Checked delivery", "Results are reviewed against the checks that apply before delivery."]],
    outcomesEyebrow: "What you can create",
    outcomesTitle: "One product. Different finished outcomes.",
    outcomesLead: "Choose the result you need. ILAIOS can combine research and production work without making you operate every underlying tool separately.",
    outcomes: [
      ["Website", "From a business goal to a responsive website with browser, accessibility and release checks.", "/factories/web"],
      ["Video", "From a brief and references to a finished media deliverable with render and quality checks.", "/factories/video"],
      ["Software", "From a bounded repository task to reviewed code, tests and change evidence.", "/factories/software"],
      ["Application", "From an application goal to build and test work inside explicit release boundaries.", "/factories/app"],
      ["Research", "From a question to source-grounded analysis with reviewable supporting evidence.", "/factories/research-data"],
    ],
    processEyebrow: "How it works",
    processTitle: "A clear path from goal to finished work.",
    process: [["01", "Goal", "Tell ILAIOS the result you want."], ["02", "Manage", "ILAIOS scopes the permitted work and dependencies."], ["03", "Produce", "The required production work is carried out inside those boundaries."], ["04", "Verify", "Applicable checks evaluate the result."], ["05", "Deliver", "Accepted work is returned with reviewable evidence."]],
    controlEyebrow: "Built-in control",
    controlTitle: "Powerful execution should still have clear boundaries.",
    controlLead: "Identity, permissions, approvals and evidence remain part of the ILAIOS control model. Technical details live in Architecture and Documentation; the product experience stays outcome-first.",
    architecture: "Explore the architecture",
    closeEyebrow: "Start with the outcome",
    closeTitle: "What do you want ILAIOS to finish?",
    closePrimary: "Explore production outcomes",
    closeSecondary: "See capabilities",
  },
  tr: {
    eyebrow: "Hedeften bitmiş sonuca",
    title: "Ne istediğini anlat. ILAIOS işi yönetip doğrulanmış sonuca taşısın.",
    lead: "Tek bir sonuçla başla. ILAIOS gereken işi koordine eder, gerekli kontrolleri uygular, sonucu doğrular ve kanıtı teslimatla birlikte tutar.",
    primary: "ILAIOS neler üretebilir?",
    secondary: "Nasıl çalışır?",
    proof: [["Tek hedef", "Araçları değil, istediğin sonucu tarif et."], ["Yönetilen yürütme", "İş açık izinler ve kontroller içinde kalır."], ["Kontrollü teslim", "Sonuç, teslimden önce geçerli kontrollerle değerlendirilir."]],
    outcomesEyebrow: "Neler üretebilirsin?",
    outcomesTitle: "Tek ürün. Farklı bitmiş sonuçlar.",
    outcomesLead: "İhtiyacın olan sonucu seç. ILAIOS, her aracı ayrı ayrı işletmeni gerektirmeden araştırma ve üretim işlerini bir araya getirebilir.",
    outcomes: [
      ["Web sitesi", "Bir iş hedefinden responsive web sitesine; tarayıcı, erişilebilirlik ve yayın kontrolleriyle.", "/tr/factories/web"],
      ["Video", "Bir brief ve referanslardan bitmiş medya çıktısına; render ve kalite kontrolleriyle.", "/tr/factories/video"],
      ["Yazılım", "Sınırları belirli bir kod deposu görevinden incelenmiş kod, test ve değişiklik kanıtına.", "/tr/factories/software"],
      ["Uygulama", "Bir uygulama hedefinden açık derleme, test ve yayın sınırları içindeki çalışmaya.", "/tr/factories/app"],
      ["Araştırma", "Bir sorudan kaynak temelli analize ve incelenebilir destekleyici kanıta.", "/tr/factories/research-data"],
    ],
    processEyebrow: "Nasıl çalışır?",
    processTitle: "Hedeften bitmiş işe uzanan açık bir yol.",
    process: [["01", "Hedef", "İstediğin sonucu ILAIOS'a anlat."], ["02", "Yönet", "ILAIOS izin verilen işi ve bağımlılıkları sınırlar."], ["03", "Üret", "Gerekli üretim işi bu sınırlar içinde yürütülür."], ["04", "Doğrula", "Geçerli kontroller sonucu değerlendirir."], ["05", "Teslim et", "Kabul edilen iş incelenebilir kanıtla sunulur."]],
    controlEyebrow: "Yerleşik kontrol",
    controlTitle: "Güçlü yürütmenin sınırları da açık olmalı.",
    controlLead: "Kimlik, izinler, onaylar ve kanıt ILAIOS kontrol modelinin parçası olarak kalır. Teknik ayrıntılar Mimari ve Dokümantasyon'da bulunur; ürün deneyimi sonuç odaklı kalır.",
    architecture: "Mimariyi incele",
    closeEyebrow: "Sonuçla başla",
    closeTitle: "ILAIOS'un neyi bitirmesini istiyorsun?",
    closePrimary: "Üretim sonuçlarını keşfet",
    closeSecondary: "Yetenekleri gör",
  },
} as const;

export default function HomePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";

  return <>
    {/* Hero Section with Motion */}
    <section className="shell page-hero compact-page-hero pt-20 pb-20" data-visual-role="home-hero">
      <div className="home-hero-copy container" data-visual-role="homepage-v2-authoritative">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
        >
          <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
          <h1 className="text-5xl font-semibold tracking-tighter mb-6">{c.title}</h1>
          <p className="text-xl leading-relaxed mb-8">{c.lead}</p>
          <div className="actions flex items-center gap-4">
            <Link className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href={`${base}/use-ilaios`}>{c.primary}</Link>
            <Link className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200" href={`${base}/how-it-works`}>{c.secondary}</Link>
          </div>
        </motion.div>
        <div className="hidden md:block">
          <Image
            src="/brand/assets/11-ilaios-website-hero.jpg"
            alt="ILAIOS Governed AI Operating System"
            width={1920}
            height={1080}
            className="rounded-lg shadow-lg"
            style={{ mixBlendMode: "lighten" }}
          />
        </div>
      </div>
    </section>
    <ProductExperience locale={locale} />
    <section className="proof-strip bg-gray-800">
      <div className="shell proof-strip-grid grid grid-cols-1 gap-6 pt-16 pb-16">
        {c.proof.map(([title, text]) => (
          <motion.div
            key={title}
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
          >
            <div key={title} className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
              <div className="flex items-start gap-4">
                <strong className="text-base font-semibold text-white">{title}</strong>
                <span className="text-base leading-relaxed">{text}</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
    <section className="section surface-section pt-20 pb-20">
      <div className="shell">
        <div className="section-heading">
          <div><div className="eyebrow text-sm tracking-wider text-gray-400">{c.outcomesEyebrow}</div><h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.outcomesTitle}</h2></div>
          <p className="text-base leading-relaxed mb-8">{c.outcomesLead}</p>
        </div>
        {/* Outcome Showcase with Motion Stagger */}
        <motion.ul
          className="outcome-showcase home-output-index-v2 grid gap-6 pt-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
        >
          {c.outcomes.map(([title, text, href], index) => (
            <motion.li
              key={title}
              className="outcome-row flex flex-col items-start gap-3 border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200"
            >
              <Link href={href}>
                <span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3 className="text-lg font-semibold mb-2">{title}</h3>
                  <p className="text-sm leading-relaxed">{text}</p>
                </div>
                <strong aria-hidden="true" className="mt-2 text-white">→</strong>
              </Link>
            </motion.li>
          ))}
        </motion.ul>
      </div>
    </section>
    <section className="section pt-20 pb-20">
      <div className="shell">
        <div className="compact-heading-row">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.processEyebrow}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.processTitle}</h2>
          </div>
        </div>
        {/* Process Rail with Motion Stagger */}
        <motion.ul
          className="process-rail home-process-rail-v2 grid gap-8 pt-8"
          data-visual-role="five-step-execution"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
        >
          {c.process.map(([n, title, text], index) => (
            <motion.li
              key={n}
              className="flex flex-col items-start gap-4"
            >
              <span className="text-xs font-bold text-gray-400">{n}</span>
              <strong className="text-lg font-semibold">{title}</strong>
              <p className="text-base leading-relaxed">{text}</p>
            </motion.li>
          ))}
        </motion.ul>
      </div>
    </section>
    <section className="section surface-section home-control-ledger-v2 pt-20 pb-20">
      <div className="shell evidence-story grid gap-8">
        <div className="evidence-story-copy">
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
          >
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.controlEyebrow}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.controlTitle}</h2>
            <p className="text-base leading-relaxed mb-6">{c.controlLead}</p>
            <Link className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200" href={`${base}/architecture`}>{c.architecture} →</Link>
          </motion.div>
        </div>
        <GovernanceEvidence locale={locale} />
      </div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <div className="shell compact-cta text-center">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
        >
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">{c.closeEyebrow}</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">{c.closeTitle}</h2>
          </div>
          <div className="actions flex items-center justify-center gap-4 mt-8">
            <Link className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href={`${base}/factories`}>{c.closePrimary}</Link>
            <Link className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200" href={`${base}/capabilities`}>{c.closeSecondary}</Link>
          </div>
        </motion.div>
      </div>
    </section>
  </>;
}