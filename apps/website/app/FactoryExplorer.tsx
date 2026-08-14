"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type Locale = "en" | "tr";

type Factory = {
  label: string;
  short: string;
  pipeline: readonly string[];
  result: string;
  boundary: string;
  href: string;
};

const data = {
  en: {
    eyebrow: "Factory explorer",
    title: "Different outcomes. One governed operating model.",
    intro: "Select a factory to inspect its production path, expected result and current authority boundary.",
    pipeline: "Workflow",
    result: "Outcome",
    boundary: "Boundary",
    open: "Open factory",
    factories: [
      { label: "Web", short: "Website production", pipeline: ["Requirements", "Design", "Build", "Browser QA", "Release evidence"], result: "Verified finished-site package", boundary: "Deployment requires explicit release authority and exact attribution.", href: "/factories/web" },
      { label: "Video / Media", short: "Media production", pipeline: ["Research", "Script", "Assets", "Render", "Validation"], result: "Validated media package", boundary: "Publishing remains separately authorized from generation and render.", href: "/factories/video" },
      { label: "Software", short: "Repository engineering", pipeline: ["Context", "Plan", "Change", "Tests", "Review evidence"], result: "Tested bounded change set", boundary: "Repository and policy scope constrain tools, files and merge authority.", href: "/factories/software" },
      { label: "App", short: "Application outcomes", pipeline: ["Scope", "Change plan", "Build plan", "Tests", "Review"], result: "Reviewable application outcome", boundary: "Current foundation does not silently acquire signing, store or deployment authority.", href: "/factories/app" },
      { label: "Research & Data", short: "Provenance-first analysis", pipeline: ["Question", "Sources", "Claims", "Analysis", "Evidence"], result: "Grounded research package", boundary: "Proposed claims remain distinct from verified facts and source evidence.", href: "/factories/research-data" },
      { label: "Security", short: "Authorized defensive work", pipeline: ["Scope", "Inspect", "Assess", "Remediate", "Verify"], result: "Defensive findings and remediation evidence", boundary: "Only explicitly authorized defensive scope may advance.", href: "/factories/security" },
      { label: "Document", short: "Controlled composition", pipeline: ["Sources", "Compose", "Validate", "Hash", "Export gate"], result: "Trusted-source document package", boundary: "Export remains approval-gated and evidence-linked.", href: "/factories/creative-document" },
      { label: "Growth", short: "Review-only growth work", pipeline: ["Evidence", "Proposal", "Draft", "Review", "Decision"], result: "Evidence-backed growth proposal", boundary: "No paid-spend or publishing authority is implied by the factory.", href: "/factories/commerce-growth" },
      { label: "Personal Ops", short: "Reviewable personal operations", pipeline: ["Goal", "Context", "Draft plan", "Review", "Approved action"], result: "Review-only personal operation plan", boundary: "Calendar, email and reminder side effects remain separately governed.", href: "/factories/personal-operations" },
    ] as readonly Factory[],
  },
  tr: {
    eyebrow: "Üretim alanları",
    title: "Farklı sonuçlar. Tek yönetim modeli.",
    intro: "Üretim yolunu, beklenen sonucu ve güncel yetki sınırını görmek için bir alan seçin.",
    pipeline: "İş akışı",
    result: "Sonuç",
    boundary: "Yetki sınırı",
    open: "Alanı aç",
    factories: [
      { label: "Web", short: "Web sitesi üretimi", pipeline: ["Gereksinimler", "Tasarım", "Geliştirme", "Tarayıcı QA", "Yayın kanıtı"], result: "Doğrulanmış bitmiş site paketi", boundary: "Yayın için açık release yetkisi ve kesin deployment eşleştirmesi gerekir.", href: "/tr/factories/web" },
      { label: "Video / Medya", short: "Medya üretimi", pipeline: ["Araştırma", "Senaryo", "Varlıklar", "Render", "Doğrulama"], result: "Doğrulanmış medya paketi", boundary: "Yayınlama yetkisi üretim ve render aşamalarından ayrı tutulur.", href: "/tr/factories/video" },
      { label: "Yazılım", short: "Repository mühendisliği", pipeline: ["Bağlam", "Plan", "Değişiklik", "Testler", "İnceleme kanıtı"], result: "Test edilmiş sınırlandırılmış değişiklik", boundary: "Repository ve politika kapsamı araç, dosya ve merge yetkisini sınırlar.", href: "/tr/factories/software" },
      { label: "Uygulama", short: "Uygulama sonuçları", pipeline: ["Kapsam", "Değişiklik planı", "Build planı", "Testler", "İnceleme"], result: "İncelenebilir uygulama sonucu", boundary: "Mevcut temel signing, store veya deployment yetkisini sessizce edinmez.", href: "/tr/factories/app" },
      { label: "Araştırma & Veri", short: "Kaynak kökenli analiz", pipeline: ["Soru", "Kaynaklar", "İddialar", "Analiz", "Kanıt"], result: "Kaynaklandırılmış araştırma paketi", boundary: "Önerilen iddialar doğrulanmış gerçeklerden ve kaynak kanıtından ayrı tutulur.", href: "/tr/factories/research-data" },
      { label: "Güvenlik", short: "Yetkili savunma çalışması", pipeline: ["Kapsam", "İnceleme", "Değerlendirme", "Düzeltme", "Doğrulama"], result: "Savunma bulguları ve düzeltme kanıtı", boundary: "Yalnızca açıkça yetkilendirilmiş savunma kapsamı ilerleyebilir.", href: "/tr/factories/security" },
      { label: "Doküman", short: "Kontrollü içerik oluşturma", pipeline: ["Kaynaklar", "Oluşturma", "Doğrulama", "Hash", "Dışa aktarma kapısı"], result: "Güvenilir kaynaklı doküman paketi", boundary: "Dışa aktarma onaya ve kanıta bağlı kalır.", href: "/tr/factories/creative-document" },
      { label: "Büyüme", short: "İnceleme odaklı büyüme", pipeline: ["Kanıt", "Öneri", "Taslak", "İnceleme", "Karar"], result: "Kanıta dayalı büyüme önerisi", boundary: "Ücretli harcama veya yayınlama yetkisi üretim alanının adıyla verilmez.", href: "/tr/factories/commerce-growth" },
      { label: "Kişisel Operasyon", short: "İncelenebilir kişisel işler", pipeline: ["Hedef", "Bağlam", "Taslak plan", "İnceleme", "Onaylı işlem"], result: "İnceleme odaklı kişisel operasyon planı", boundary: "Takvim, e-posta ve hatırlatıcı yan etkileri ayrıca yönetilir.", href: "/tr/factories/personal-operations" },
    ] as readonly Factory[],
  },
} as const;

export default function FactoryExplorer({ locale }: { locale: Locale }) {
  const c = data[locale];
  const [active, setActive] = useState(0);
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const factory = c.factories[active];

  const move = (next: number) => {
    const index = (next + c.factories.length) % c.factories.length;
    setActive(index);
    refs.current[index]?.focus();
  };

  return <div className="factory-explorer" data-visual-role="factory-explorer">
    <div className="factory-explorer-heading"><div><span className="micro-label">{c.eyebrow}</span><h2>{c.title}</h2></div><p>{c.intro}</p></div>
    <div className="factory-explorer-layout">
      <div className="factory-index" role="tablist" aria-label={locale === "tr" ? "Üretim alanları" : "Factories"}>
        {c.factories.map((item, index) => <button
          type="button"
          role="tab"
          aria-selected={active === index}
          tabIndex={active === index ? 0 : -1}
          className={active === index ? "is-active" : ""}
          key={item.href}
          ref={element => { refs.current[index] = element; }}
          onClick={() => setActive(index)}
          onMouseEnter={() => setActive(index)}
          onKeyDown={event => {
            if (event.key === "ArrowDown" || event.key === "ArrowRight") { event.preventDefault(); move(active + 1); }
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") { event.preventDefault(); move(active - 1); }
          }}
        ><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.label}</strong><small>{item.short}</small></button>)}
      </div>
      <div className="factory-detail" role="tabpanel" tabIndex={0}>
        <div className="factory-detail-top"><div><span className="micro-label">{factory.label}</span><h3>{factory.result}</h3></div><Link className="text-link" href={factory.href}>{c.open} →</Link></div>
        <div className="factory-pipeline"><span>{c.pipeline}</span><ol>{factory.pipeline.map((step, index) => <li key={step}><small>{String(index + 1).padStart(2, "0")}</small><strong>{step}</strong></li>)}</ol></div>
        <div className="factory-boundary"><span>{c.boundary}</span><p>{factory.boundary}</p></div>
      </div>
    </div>
  </div>;
}
