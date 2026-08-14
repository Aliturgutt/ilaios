"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type Locale = "en" | "tr";
type ModeKey = "web" | "video" | "software" | "app";

type Mode = {
  key: ModeKey;
  label: string;
  prompt: string;
  result: string;
  artifact: string;
  evidence: readonly string[];
  href: string;
};

const copy = {
  en: {
    label: "Product experience",
    title: "One goal in. A governed workflow out.",
    note: "Interactive canonical workflow preview — no external side effects are performed here.",
    inputLabel: "Describe the outcome",
    run: "Preview workflow",
    rerun: "Run again",
    stages: ["Planning", "Building", "Validating", "Finished"],
    preview: "Canonical preview",
    evidence: "Acceptance evidence",
    open: "Open factory",
    modes: [
      { key: "web", label: "Website", prompt: "Create a product website with EN/TR pages, responsive QA and verified deployment evidence.", result: "Verified website package", artifact: "site + QA + release evidence", evidence: ["Responsive checks", "Accessibility & SEO", "Release attribution"], href: "/factories/web" },
      { key: "video", label: "Video", prompt: "Create a product launch video from research through render and validation.", result: "Validated media package", artifact: "script + assets + render evidence", evidence: ["Source provenance", "Render validation", "Delivery manifest"], href: "/factories/video" },
      { key: "software", label: "Software", prompt: "Implement a bounded repository change with tests, review gates and evidence.", result: "Tested change set", artifact: "code + tests + review evidence", evidence: ["Repository context", "Deterministic tests", "Change evidence"], href: "/factories/software" },
      { key: "app", label: "Application", prompt: "Prepare a governed application change and validation plan without silent deployment authority.", result: "Reviewable application outcome", artifact: "change plan + build/test evidence", evidence: ["Protected roots", "Build/test plan", "Approval boundary"], href: "/factories/app" },
    ] as readonly Mode[],
  },
  tr: {
    label: "Ürün deneyimi",
    title: "Tek hedef girer. Yönetilen bir iş akışı çıkar.",
    note: "Etkileşimli kanonik iş akışı önizlemesi — burada dış sistemlerde işlem yapılmaz.",
    inputLabel: "Bitmesini istediğiniz sonucu tarif edin",
    run: "İş akışını önizle",
    rerun: "Yeniden çalıştır",
    stages: ["Planlama", "Üretim", "Doğrulama", "Tamamlandı"],
    preview: "Kanonik önizleme",
    evidence: "Kabul kanıtı",
    open: "Üretim alanını aç",
    modes: [
      { key: "web", label: "Web sitesi", prompt: "EN/TR sayfaları, responsive QA ve doğrulanmış yayın kanıtı olan bir ürün sitesi oluştur.", result: "Doğrulanmış web sitesi paketi", artifact: "site + QA + yayın kanıtı", evidence: ["Responsive kontroller", "Erişilebilirlik ve SEO", "Yayın eşleştirmesi"], href: "/tr/factories/web" },
      { key: "video", label: "Video", prompt: "Araştırmadan render ve doğrulamaya kadar ürün lansman videosu oluştur.", result: "Doğrulanmış medya paketi", artifact: "senaryo + varlıklar + render kanıtı", evidence: ["Kaynak kökeni", "Render doğrulaması", "Teslim manifestosu"], href: "/tr/factories/video" },
      { key: "software", label: "Yazılım", prompt: "Testler, inceleme kapıları ve kanıtla sınırlandırılmış bir repository değişikliği uygula.", result: "Test edilmiş değişiklik paketi", artifact: "kod + testler + inceleme kanıtı", evidence: ["Repository bağlamı", "Deterministik testler", "Değişiklik kanıtı"], href: "/tr/factories/software" },
      { key: "app", label: "Uygulama", prompt: "Sessiz deployment yetkisi olmadan yönetilen uygulama değişikliği ve doğrulama planı hazırla.", result: "İncelenebilir uygulama sonucu", artifact: "değişiklik planı + build/test kanıtı", evidence: ["Korunan kökler", "Build/test planı", "Onay sınırı"], href: "/tr/factories/app" },
    ] as readonly Mode[],
  },
} as const;

export default function ProductExperience({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [modeIndex, setModeIndex] = useState(0);
  const [phase, setPhase] = useState(0);
  const [running, setRunning] = useState(false);
  const [goal, setGoal] = useState(c.modes[0].prompt);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const mode = c.modes[modeIndex];

  useEffect(() => {
    if (!running) return;
    const timer = window.setTimeout(() => {
      if (phase >= c.stages.length - 1) setRunning(false);
      else setPhase(value => value + 1);
    }, 620);
    return () => window.clearTimeout(timer);
  }, [running, phase, c.stages.length]);

  const selectMode = (index: number) => {
    setModeIndex(index);
    setGoal(c.modes[index].prompt);
    setPhase(0);
    setRunning(false);
  };

  const moveTab = (next: number) => {
    const index = (next + c.modes.length) % c.modes.length;
    selectMode(index);
    tabRefs.current[index]?.focus();
  };

  const runPreview = () => {
    setPhase(0);
    setRunning(true);
  };

  return <div className="product-experience" data-visual-role="interactive-product-demo">
    <div className="product-experience-head">
      <div><span className="micro-label">{c.label}</span><h2>{c.title}</h2></div>
      <p>{c.note}</p>
    </div>

    <div className="product-mode-tabs" role="tablist" aria-label={locale === "tr" ? "Ürün sonucu türü" : "Product outcome type"}>
      {c.modes.map((item, index) => <button
        key={item.key}
        ref={element => { tabRefs.current[index] = element; }}
        type="button"
        role="tab"
        aria-selected={modeIndex === index}
        tabIndex={modeIndex === index ? 0 : -1}
        className={modeIndex === index ? "is-active" : ""}
        onClick={() => selectMode(index)}
        onKeyDown={event => {
          if (event.key === "ArrowRight") { event.preventDefault(); moveTab(modeIndex + 1); }
          if (event.key === "ArrowLeft") { event.preventDefault(); moveTab(modeIndex - 1); }
          if (event.key === "Home") { event.preventDefault(); moveTab(0); }
          if (event.key === "End") { event.preventDefault(); moveTab(c.modes.length - 1); }
        }}
      >{item.label}</button>)}
    </div>

    <div className="product-experience-grid">
      <div className="goal-composer">
        <label htmlFor={`goal-${locale}`}>{c.inputLabel}</label>
        <textarea id={`goal-${locale}`} value={goal} onChange={event => setGoal(event.target.value)} rows={4} />
        <div className="composer-actions">
          <button className="button" type="button" onClick={runPreview} disabled={running}>{phase === c.stages.length - 1 ? c.rerun : c.run}</button>
          <Link className="text-link" href={mode.href}>{c.open} →</Link>
        </div>
      </div>

      <div className="execution-preview" aria-live="polite">
        <div className="execution-status-line"><span>{c.preview}</span><strong>{c.stages[phase]}</strong></div>
        <div className="execution-rail" aria-label={locale === "tr" ? "İş akışı durumu" : "Workflow status"}>
          {c.stages.map((stage, index) => <div key={stage} className={`${index < phase ? "is-complete" : ""} ${index === phase ? "is-active" : ""}`}><span>{String(index + 1).padStart(2, "0")}</span><small>{stage}</small></div>)}
        </div>
        <div className="result-preview">
          <span>{mode.result}</span>
          <strong>{mode.artifact}</strong>
          <div className="result-lines" aria-hidden="true"><i /><i /><i /></div>
        </div>
        <div className="evidence-preview"><span>{c.evidence}</span><ul>{mode.evidence.map(item => <li key={item}>{item}</li>)}</ul></div>
      </div>
    </div>
  </div>;
}
