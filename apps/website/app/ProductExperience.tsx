// Importers/callers: Imported by HomePage.tsx
// Affected API: React component using next/link and react hooks (useState, useRef)
// Data schemas: Props (locale: Locale), state (modeIndex, stageIndex), refs (tabRefs)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useRef, useState } from "react";

type Locale = "en" | "tr";
type ModeKey = "web" | "video" | "software" | "app";
type Mode = { key: ModeKey; label: string; prompt: string; result: string; checks: readonly string[]; href: string };

const copy = {
  en: {
    label: "Interactive canonical workflow preview",
    title: "One request can become finished work.",
    note: "Illustrative interactive preview with no external side effects. It does not execute providers or create production work.",
    request: "Example request",
    delivery: "What the finished path includes",
    checks: "Typical checks",
    open: "Explore this outcome",
    stages: ["Planning", "Building", "Validating", "Finished"],
    stageNotes: ["The goal is scoped into permitted work and dependencies.", "The selected production path carries out the bounded work.", "Applicable checks evaluate the current result.", "Accepted work is ready to return with reviewable evidence."],
    modes: [
      { key: "web", label: "Website", prompt: "Create a premium website for my furniture business.", result: "Responsive site, EN/TR-ready structure and release evidence when publishing is authorized.", checks: ["Browser QA", "Accessibility and SEO", "Broken-asset and release checks"], href: "/factories/web" },
      { key: "video", label: "Video", prompt: "Create a launch video from my brief and references.", result: "A rendered media deliverable with reference-aware production and delivery evidence.", checks: ["Reference consistency", "Render validation", "Delivery checks"], href: "/factories/video" },
      { key: "software", label: "Software", prompt: "Implement this bounded change in my repository.", result: "Reviewed code, focused tests and evidence for the exact change.", checks: ["Repository scope", "Automated tests", "Change evidence"], href: "/factories/software" },
      { key: "app", label: "Application", prompt: "Prepare this application outcome inside explicit release boundaries.", result: "Application work with build and test evidence before any release step.", checks: ["Protected scope", "Build and test", "Release boundary"], href: "/factories/app" },
    ] as readonly Mode[],
  },
  tr: {
    label: "Dört örnek iş akışı · 9 üretim alanından örnekler",
    title: "Tek bir istek bitmiş işe dönüşebilir.",
    note: "Bu dört sekme, dokuz üretim alanından yalnızca örnek akışları gösterir. Dış sistemlerde yan etki oluşturmaz; sağlayıcı çalıştırmaz veya gerçek üretim işi başlatmaz.",
    request: "Örnek istek",
    delivery: "Bitmiş yolun içerdiği sonuç",
    checks: "Tipik kontroller",
    open: "Bu sonucu keşfet",
    stages: ["Planlama", "Üretim", "Doğrulama", "Tamamlandı"],
    stageNotes: ["Hedef, izin verilen iş ve bağımlılıklar halinde sınırlandırılır.", "Seçilen üretim yolu sınırlandırılmış işi yürütür.", "Geçerli kontroller mevcut sonucu değerlendirir.", "Kabul edilen iş incelenebilir kanıtla teslim edilmeye hazırdır."],
    modes: [
      { key: "web", label: "Web sitesi", prompt: "Mobilya şirketim için üst düzey bir web sitesi oluştur.", result: "Duyarlı site, EN/TR'ye hazır yapı ve yayın yetkilendirildiğinde yayın kanıtı.", checks: ["Tarayıcı kalite kontrolü", "Erişilebilirlik ve SEO", "Kırık varlık ve yayın kontrolleri"], href: "/tr/factories/web" },
      { key: "video", label: "Video", prompt: "Proje özeti ve referanslarımdan lansman videosu oluştur.", result: "Referansları dikkate alan üretim ve teslim kanıtıyla işlenmiş medya çıktısı.", checks: ["Referans tutarlılığı", "Görüntü işleme doğrulaması", "Teslim kontrolleri"], href: "/tr/factories/video" },
      { key: "software", label: "Yazılım", prompt: "Kod depomda sınırları belirli bu değişikliği uygula.", result: "Tam değişikliğe ait incelenmiş kod, odaklı testler ve kanıt.", checks: ["Kod deposu kapsamı", "Otomatik testler", "Değişiklik kanıtı"], href: "/tr/factories/software" },
      { key: "app", label: "Uygulama", prompt: "Bu uygulama sonucunu açık yayın sınırları içinde hazırla.", result: "Herhangi bir yayın adımından önce derleme ve test kanıtı bulunan uygulama çalışması.", checks: ["Korunan kapsam", "Derleme ve test", "Yayın sınırı"], href: "/tr/factories/app" },
    ] as readonly Mode[],
  },
} as const;

export default function ProductExperience({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [modeIndex, setModeIndex] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const mode = c.modes[modeIndex];
  const moveTab = (next: number) => { const index = (next + c.modes.length) % c.modes.length; setModeIndex(index); setStageIndex(0); tabRefs.current[index]?.focus(); };

  return <div className="product-experience flex flex-col items-start gap-6 bg-gray-900 rounded-lg p-6 hover-lift" data-visual-role="interactive-product-demo">
    <div className="product-experience-head flex flex-col items-start gap-4 w-full">
      <motion.div
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div><span className="micro-label text-xs font-semibold tracking-wider text-gray-400">{c.label}</span><h2 className="text-3xl font-semibold tracking-tighter">{c.title}</h2></div>
      </motion.div>
      <motion.div
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1], delay: 0.2 } }}
      >
        <p className="text-base leading-relaxed text-gray-300">{c.note}</p>
      </motion.div>
    </div>
    <div className="product-mode-tabs flex flex-wrap items-center gap-3" role="tablist" aria-label={locale === "tr" ? "Sonuç türü" : "Outcome type"}>
      {c.modes.map((item, index) => (
        <motion.li
          key={item.key}
          initial={{ x: -10, opacity: 0 }}
          whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
        >
          <button ref={element => { tabRefs.current[index] = element; }} type="button" role="tab" aria-selected={modeIndex === index} tabIndex={modeIndex === index ? 0 : -1} className={`${modeIndex === index ? "bg-gray-800 text-white" : "bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white hover-lift hover-scale"} px-3 py-2 rounded-md font-medium transition-colors duration-200`} onClick={() => { setModeIndex(index); setStageIndex(0); }} onKeyDown={event => { if (event.key === "ArrowRight") { event.preventDefault(); moveTab(modeIndex + 1); } if (event.key === "ArrowLeft") { event.preventDefault(); moveTab(modeIndex - 1); } if (event.key === "Home") { event.preventDefault(); moveTab(0); } if (event.key === "End") { event.preventDefault(); moveTab(c.modes.length - 1); } }}>{item.label}</button>
        </motion.li>
      ))}
    </div>
    <div className="product-experience-grid grid gap-6 w-full" role="tabpanel">
      <motion.ul
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1 }}
        transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
      >
        <motion.li key="goal-composer">
          <div className="goal-composer flex flex-col items-start gap-4">
            <motion.span
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4 } }}
            >
              <span className="micro-label text-xs font-semibold tracking-wider text-gray-400">{c.request}</span>
            </motion.span>
            <motion.blockquote
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
            >
              <blockquote className="text-base leading-relaxed text-gray-400">{mode.prompt}</blockquote>
            </motion.blockquote>
            <motion.a
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.4 } }}
              className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift"
              href={mode.href}
            >
              {c.open} →
            </motion.a>
          </div>
        </motion.li>
        <motion.li key="execution-preview">
          <div className="execution-preview grid gap-6">
            <div className="result-preview flex flex-col items-start gap-2">
              <motion.span
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4 } }}
              >
                <span className="text-xs font-semibold tracking-wider text-gray-400">{c.delivery}</span>
              </motion.span>
              <motion.strong
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
                className="text-lg font-semibold text-white"
              >
                {mode.result}
              </motion.strong>
            </div>
            <div className="evidence-preview flex flex-col items-start gap-2">
              <motion.span
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4 } }}
              >
                <span className="text-xs font-semibold tracking-wider text-gray-400">{c.checks}</span>
              </motion.span>
              <motion.ul
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                className="space-y-1"
                transition={{ delayChildren: 0.1, staggerChildren: 0.15 }}
              >
                {mode.checks.map((item, idx) => (
                  <motion.li
                    key={item}
                    initial={{ x: -5, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1, transition: { duration: 0.3, delay: idx * 0.1 } }}
                    className="text-base leading-relaxed text-gray-300"
                  >
                    {item}
                  </motion.li>
                ))}
              </motion.ul>
            </div>
          </div>
        </motion.li>
      </motion.ul>
    </div>
    <div className="product-stage-control flex flex-col items-start gap-4 w-full" aria-label={locale === "tr" ? "Önizleme aşaması" : "Preview stage"}>
      <div className="product-stage-tabs flex flex-wrap items-center gap-2">
        {c.stages.map((stage, index) => (
          <motion.button
            key={stage}
            initial={{ y: -5, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1, transition: { duration: 0.3, delay: index * 0.1 } }}
            type="button"
            aria-pressed={stageIndex === index}
            className={`${stageIndex === index ? "bg-gray-800 text-white" : "bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white hover-lift"} px-2 py-1 rounded-md font-medium transition-colors duration-200`}
            onClick={() => setStageIndex(index)}
          >
            {stage}
          </motion.button>
        ))}
      </div>
      <motion.p
        initial={{ x: -10, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4 } }}
        aria-live="polite"
        className="text-base leading-relaxed text-gray-300"
      >
        {c.stageNotes[stageIndex]}
      </motion.p>
    </div>
  </div>;
}
