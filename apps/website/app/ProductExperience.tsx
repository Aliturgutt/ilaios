"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type Locale = "en" | "tr";
type ModeKey = "web" | "video" | "software" | "app";
type Mode = { key: ModeKey; label: string; prompt: string; result: string; checks: readonly string[]; href: string };

const copy = {
  en: {
    label: "Example outcome",
    title: "One request can become finished work.",
    note: "Illustrative product flow. This preview does not execute providers or create production work.",
    request: "Example request",
    delivery: "What the finished path includes",
    checks: "Typical checks",
    open: "Explore this outcome",
    modes: [
      { key: "web", label: "Website", prompt: "Create a premium website for my furniture business.", result: "Responsive site, EN/TR-ready structure and release evidence when publishing is authorized.", checks: ["Browser QA", "Accessibility and SEO", "Broken-asset and release checks"], href: "/factories/web" },
      { key: "video", label: "Video", prompt: "Create a launch video from my brief and references.", result: "A rendered media deliverable with reference-aware production and delivery evidence.", checks: ["Reference consistency", "Render validation", "Delivery checks"], href: "/factories/video" },
      { key: "software", label: "Software", prompt: "Implement this bounded change in my repository.", result: "Reviewed code, focused tests and evidence for the exact change.", checks: ["Repository scope", "Automated tests", "Change evidence"], href: "/factories/software" },
      { key: "app", label: "Application", prompt: "Prepare this application outcome inside explicit release boundaries.", result: "Application work with build and test evidence before any release step.", checks: ["Protected scope", "Build and test", "Release boundary"], href: "/factories/app" },
    ] as readonly Mode[],
  },
  tr: {
    label: "Örnek sonuç",
    title: "Tek bir istek bitmiş işe dönüşebilir.",
    note: "Bu açıklayıcı bir ürün akışıdır. Buradaki önizleme sağlayıcı çalıştırmaz veya production işi oluşturmaz.",
    request: "Örnek istek",
    delivery: "Bitmiş yolun içerdiği sonuç",
    checks: "Tipik kontroller",
    open: "Bu sonucu keşfet",
    modes: [
      { key: "web", label: "Web sitesi", prompt: "Mobilya şirketim için premium bir web sitesi oluştur.", result: "Responsive site, EN/TR'ye hazır yapı ve yayın yetkilendirildiğinde release kanıtı.", checks: ["Tarayıcı QA", "Erişilebilirlik ve SEO", "Kırık varlık ve yayın kontrolleri"], href: "/tr/factories/web" },
      { key: "video", label: "Video", prompt: "Brief ve referanslarımdan lansman videosu oluştur.", result: "Referansları dikkate alan üretim ve teslim kanıtıyla render edilmiş medya çıktısı.", checks: ["Referans tutarlılığı", "Render doğrulaması", "Teslim kontrolleri"], href: "/tr/factories/video" },
      { key: "software", label: "Yazılım", prompt: "Kod depomda sınırları belirli bu değişikliği uygula.", result: "Tam değişikliğe ait incelenmiş kod, odaklı testler ve kanıt.", checks: ["Kod deposu kapsamı", "Otomatik testler", "Değişiklik kanıtı"], href: "/tr/factories/software" },
      { key: "app", label: "Uygulama", prompt: "Bu uygulama sonucunu açık yayın sınırları içinde hazırla.", result: "Herhangi bir yayın adımından önce derleme ve test kanıtı bulunan uygulama çalışması.", checks: ["Korunan kapsam", "Derleme ve test", "Yayın sınırı"], href: "/tr/factories/app" },
    ] as readonly Mode[],
  },
} as const;

export default function ProductExperience({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [modeIndex, setModeIndex] = useState(0);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const mode = c.modes[modeIndex];
  const selectMode = (index: number) => setModeIndex(index);
  const moveTab = (next: number) => {
    const index = (next + c.modes.length) % c.modes.length;
    selectMode(index);
    tabRefs.current[index]?.focus();
  };

  return <div className="product-experience" data-visual-role="illustrative-product-outcome">
    <div className="product-experience-head"><div><span className="micro-label">{c.label}</span><h2>{c.title}</h2></div><p>{c.note}</p></div>
    <div className="product-mode-tabs" role="tablist" aria-label={locale === "tr" ? "Sonuç türü" : "Outcome type"}>
      {c.modes.map((item, index) => <button key={item.key} ref={element => { tabRefs.current[index] = element; }} type="button" role="tab" aria-selected={modeIndex === index} tabIndex={modeIndex === index ? 0 : -1} className={modeIndex === index ? "is-active" : ""} onClick={() => selectMode(index)} onKeyDown={event => { if (event.key === "ArrowRight") { event.preventDefault(); moveTab(modeIndex + 1); } if (event.key === "ArrowLeft") { event.preventDefault(); moveTab(modeIndex - 1); } if (event.key === "Home") { event.preventDefault(); moveTab(0); } if (event.key === "End") { event.preventDefault(); moveTab(c.modes.length - 1); } }}>{item.label}</button>)}
    </div>
    <div className="product-example-body" role="tabpanel">
      <div><span className="micro-label">{c.request}</span><blockquote>{mode.prompt}</blockquote></div>
      <div><span className="micro-label">{c.delivery}</span><p>{mode.result}</p></div>
      <div><span className="micro-label">{c.checks}</span><ul>{mode.checks.map(item => <li key={item}>{item}</li>)}</ul></div>
      <Link className="text-link" href={mode.href}>{c.open} →</Link>
    </div>
  </div>;
}
