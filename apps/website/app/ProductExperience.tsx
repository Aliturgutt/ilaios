"use client";

import Link from "next/link";
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
    label: "Etkileşimli kanonik iş akışı önizlemesi",
    title: "Tek bir istek bitmiş işe dönüşebilir.",
    note: "Dış sistemlerde hiçbir yan etki oluşturmayan açıklayıcı ve etkileşimli bir önizlemedir. Sağlayıcı çalıştırmaz veya production işi oluşturmaz.",
    request: "Örnek istek",
    delivery: "Bitmiş yolun içerdiği sonuç",
    checks: "Tipik kontroller",
    open: "Bu sonucu keşfet",
    stages: ["Planlama", "Üretim", "Doğrulama", "Tamamlandı"],
    stageNotes: ["Hedef, izin verilen iş ve bağımlılıklar halinde sınırlandırılır.", "Seçilen üretim yolu sınırlandırılmış işi yürütür.", "Geçerli kontroller mevcut sonucu değerlendirir.", "Kabul edilen iş incelenebilir kanıtla teslim edilmeye hazırdır."],
    modes: [
      { key: "web", label: "Web sitesi", prompt: "Mobilya şirketim için premium bir web sitesi oluştur.", result: "Responsive site, EN/TR'ye hazır yapı ve yayın yetkilendirildiğinde yayın kanıtı.", checks: ["Tarayıcı QA", "Erişilebilirlik ve SEO", "Kırık varlık ve yayın kontrolleri"], href: "/tr/factories/web" },
      { key: "video", label: "Video", prompt: "Brief ve referanslarımdan lansman videosu oluştur.", result: "Referansları dikkate alan üretim ve teslim kanıtıyla render edilmiş medya çıktısı.", checks: ["Referans tutarlılığı", "Render doğrulaması", "Teslim kontrolleri"], href: "/tr/factories/video" },
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

  return <div className="product-experience" data-visual-role="interactive-product-demo">
    <div className="product-experience-head"><div><span className="micro-label">{c.label}</span><h2>{c.title}</h2></div><p>{c.note}</p></div>
    <div className="product-mode-tabs" role="tablist" aria-label={locale === "tr" ? "Sonuç türü" : "Outcome type"}>
      {c.modes.map((item, index) => <button key={item.key} ref={element => { tabRefs.current[index] = element; }} type="button" role="tab" aria-selected={modeIndex === index} tabIndex={modeIndex === index ? 0 : -1} className={modeIndex === index ? "is-active" : ""} onClick={() => { setModeIndex(index); setStageIndex(0); }} onKeyDown={event => { if (event.key === "ArrowRight") { event.preventDefault(); moveTab(modeIndex + 1); } if (event.key === "ArrowLeft") { event.preventDefault(); moveTab(modeIndex - 1); } if (event.key === "Home") { event.preventDefault(); moveTab(0); } if (event.key === "End") { event.preventDefault(); moveTab(c.modes.length - 1); } }}>{item.label}</button>)}
    </div>
    <div className="product-experience-grid" role="tabpanel">
      <div className="goal-composer"><span className="micro-label">{c.request}</span><blockquote>{mode.prompt}</blockquote><Link className="text-link" href={mode.href}>{c.open} →</Link></div>
      <div className="execution-preview"><div className="result-preview"><span>{c.delivery}</span><strong>{mode.result}</strong></div><div className="evidence-preview"><span>{c.checks}</span><ul>{mode.checks.map(item => <li key={item}>{item}</li>)}</ul></div></div>
    </div>
    <div className="product-stage-control" aria-label={locale === "tr" ? "Önizleme aşaması" : "Preview stage"}>
      <div className="product-stage-tabs">{c.stages.map((stage, index) => <button key={stage} type="button" aria-pressed={stageIndex === index} className={stageIndex === index ? "is-active" : ""} onClick={() => setStageIndex(index)}>{stage}</button>)}</div>
      <p aria-live="polite">{c.stageNotes[stageIndex]}</p>
    </div>
  </div>;
}
