"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type Locale = "en" | "tr";
type Availability = "preview" | "development";

type Factory = {
  label: string;
  short: string;
  pipeline: readonly string[];
  result: string;
  boundary: string;
  href: string;
  availability: Availability;
  availabilityLabel: string;
  availabilityDetail: string;
};

const data = {
  en: {
    eyebrow: "Factory explorer",
    title: "Different outcomes. One governed operating model.",
    intro: "Select a factory to inspect its production path, target result, current public readiness and authority boundary.",
    pipeline: "Workflow",
    result: "Outcome",
    boundary: "Boundary",
    current: "Current readiness",
    open: "Open factory",
    factories: [
      { label: "Web", short: "Website production", pipeline: ["Requirements", "Design", "Build", "Browser QA", "Release evidence"], result: "Finished-site target with QA and release evidence", boundary: "Deployment requires explicit release authority and exact attribution.", href: "/factories/web", availability: "preview", availabilityLabel: "Preview", availabilityDetail: "Repository-bounded Web production is evidence-backed; canonical-domain production remains separately verified." },
      { label: "Video / Media", short: "Media production", pipeline: ["Research", "Script", "Assets", "Render", "Validation"], result: "Finished-media target with validation evidence", boundary: "Publishing remains separately authorized from generation and render.", href: "/factories/video", availability: "preview", availabilityLabel: "Preview", availabilityDetail: "Bounded finished-product E2E exists; live zero-cost external provider availability remains evidence-gated." },
      { label: "Software", short: "Repository engineering", pipeline: ["Context", "Plan", "Change", "Tests", "Review evidence"], result: "Tested bounded change set", boundary: "Repository and policy scope constrain tools, files and merge authority.", href: "/factories/software", availability: "preview", availabilityLabel: "Preview", availabilityDetail: "Verified bounded local Windows scope does not imply arbitrary external-repository or commercial-release breadth." },
      { label: "App", short: "Application outcomes", pipeline: ["Scope", "Product/UX", "Build", "Tests", "Release readiness"], result: "Windows-first application outcome with evidence", boundary: "Android/iOS, signing, Store publication and broader app breadth remain separate gates.", href: "/factories/app", availability: "preview", availabilityLabel: "Preview", availabilityDetail: "Bounded Windows finished-product evidence exists; mobile and Store release are not claimed as generally available." },
      { label: "Research & Data", short: "Provenance-first analysis", pipeline: ["Question", "Sources", "Claims", "Analysis", "Evidence"], result: "Grounded research target", boundary: "Proposed claims remain distinct from verified facts and source evidence.", href: "/factories/research-data", availability: "development", availabilityLabel: "In development", availabilityDetail: "Public finished-product readiness is not established by the current factory evidence snapshot." },
      { label: "Security", short: "Authorized defensive work", pipeline: ["Scope", "Inspect", "Assess", "Remediate", "Verify"], result: "Defensive findings and remediation evidence", boundary: "Only explicitly authorized defensive scope may advance.", href: "/factories/security", availability: "development", availabilityLabel: "In development", availabilityDetail: "Security capabilities remain authorization-bound and are not presented as a generally available production service." },
      { label: "Document", short: "Controlled composition", pipeline: ["Sources", "Compose", "Validate", "Hash", "Export gate"], result: "Trusted-source document target", boundary: "Export remains approval-gated and evidence-linked.", href: "/factories/creative-document", availability: "development", availabilityLabel: "In development", availabilityDetail: "The target workflow is documented, but public finished-product readiness remains evidence-gated." },
      { label: "Growth", short: "Review-only growth work", pipeline: ["Evidence", "Proposal", "Draft", "Review", "Decision"], result: "Evidence-backed growth proposal", boundary: "No paid-spend or publishing authority is implied by the factory.", href: "/factories/commerce-growth", availability: "development", availabilityLabel: "In development", availabilityDetail: "Paid spend, publishing and production growth automation are not implied by the public factory surface." },
      { label: "Personal Ops", short: "Reviewable personal operations", pipeline: ["Goal", "Context", "Draft plan", "Review", "Approved action"], result: "Reviewable personal-operation target", boundary: "Calendar, email and reminder side effects remain separately governed.", href: "/factories/personal-operations", availability: "development", availabilityLabel: "In development", availabilityDetail: "External personal side effects remain separate governed capabilities rather than an assumed factory permission." },
    ] as readonly Factory[],
  },
  tr: {
    eyebrow: "Üretim alanları",
    title: "Farklı sonuçlar. Tek yönetim modeli.",
    intro: "Üretim yolunu, hedef sonucu, güncel public readiness seviyesini ve yetki sınırını görmek için bir alan seçin.",
    pipeline: "İş akışı",
    result: "Sonuç",
    boundary: "Yetki sınırı",
    current: "Güncel readiness",
    open: "Alanı aç",
    factories: [
      { label: "Web", short: "Web sitesi üretimi", pipeline: ["Gereksinim", "Tasarım", "Geliştirme", "Tarayıcı QA", "Yayın kanıtı"], result: "QA ve release evidence içeren bitmiş-site hedefi", boundary: "Yayın için açık release yetkisi ve kesin yayın eşleştirmesi gerekir.", href: "/tr/factories/web", availability: "preview", availabilityLabel: "Önizleme", availabilityDetail: "Repository-bounded Web üretimi kanıtlıdır; canonical-domain production ayrıca doğrulanır." },
      { label: "Video / Medya", short: "Medya üretimi", pipeline: ["Araştırma", "Senaryo", "Varlıklar", "Render", "Doğrulama"], result: "Doğrulama kanıtlı bitmiş-medya hedefi", boundary: "Yayınlama yetkisi üretim ve render aşamalarından ayrı tutulur.", href: "/tr/factories/video", availability: "preview", availabilityLabel: "Önizleme", availabilityDetail: "Bounded finished-product E2E vardır; canlı sıfır maliyetli dış provider erişilebilirliği ayrıca kanıtlanır." },
      { label: "Yazılım", short: "Kod deposu mühendisliği", pipeline: ["Bağlam", "Plan", "Değişiklik", "Testler", "İnceleme kanıtı"], result: "Test edilmiş sınırlandırılmış değişiklik", boundary: "Kod deposu ve politika kapsamı araç, dosya ve merge yetkisini sınırlar.", href: "/tr/factories/software", availability: "preview", availabilityLabel: "Önizleme", availabilityDetail: "Verified bounded local Windows kapsamı, keyfi dış repository veya ticari release genişliği anlamına gelmez." },
      { label: "Uygulama", short: "Uygulama sonuçları", pipeline: ["Kapsam", "Ürün/UX", "Build", "Testler", "Release readiness"], result: "Kanıtlı Windows-first uygulama sonucu", boundary: "Android/iOS, signing, Store publication ve daha geniş app kapsamı ayrı kapılardır.", href: "/tr/factories/app", availability: "preview", availabilityLabel: "Önizleme", availabilityDetail: "Bounded Windows finished-product evidence vardır; mobil ve Store release genel kullanıma açık diye sunulmaz." },
      { label: "Araştırma & Veri", short: "Kaynak kökenli analiz", pipeline: ["Soru", "Kaynaklar", "İddialar", "Analiz", "Kanıt"], result: "Kaynaklandırılmış araştırma hedefi", boundary: "Önerilen iddialar doğrulanmış gerçeklerden ve kaynak kanıtından ayrı tutulur.", href: "/tr/factories/research-data", availability: "development", availabilityLabel: "Geliştiriliyor", availabilityDetail: "Güncel factory evidence snapshot'ı public finished-product readiness kanıtlamaz." },
      { label: "Güvenlik", short: "Yetkili savunma çalışması", pipeline: ["Kapsam", "İnceleme", "Değerlendirme", "Düzeltme", "Doğrulama"], result: "Savunma bulguları ve düzeltme kanıtı", boundary: "Yalnızca açıkça yetkilendirilmiş savunma kapsamı ilerleyebilir.", href: "/tr/factories/security", availability: "development", availabilityLabel: "Geliştiriliyor", availabilityDetail: "Güvenlik yetenekleri yetkilendirme sınırında kalır; genel production hizmeti gibi sunulmaz." },
      { label: "Doküman", short: "Kontrollü içerik oluşturma", pipeline: ["Kaynaklar", "Oluşturma", "Doğrulama", "Hash", "Dışa aktarma kapısı"], result: "Güvenilir kaynaklı doküman hedefi", boundary: "Dışa aktarma onaya ve kanıta bağlı kalır.", href: "/tr/factories/creative-document", availability: "development", availabilityLabel: "Geliştiriliyor", availabilityDetail: "Hedef workflow tanımlıdır; public finished-product readiness ayrıca evidence-gated kalır." },
      { label: "Büyüme", short: "İnceleme odaklı büyüme", pipeline: ["Kanıt", "Öneri", "Taslak", "İnceleme", "Karar"], result: "Kanıta dayalı büyüme önerisi", boundary: "Ücretli harcama veya yayınlama yetkisi factory adıyla verilmez.", href: "/tr/factories/commerce-growth", availability: "development", availabilityLabel: "Geliştiriliyor", availabilityDetail: "Ücretli harcama, yayınlama veya production growth automation factory adıyla varsayılmaz." },
      { label: "Kişisel Operasyon", short: "İncelenebilir kişisel işler", pipeline: ["Hedef", "Bağlam", "Taslak plan", "İnceleme", "Onaylı işlem"], result: "İncelenebilir kişisel operasyon hedefi", boundary: "Takvim, e-posta ve hatırlatıcı dış etkileri ayrıca yönetilir.", href: "/tr/factories/personal-operations", availability: "development", availabilityLabel: "Geliştiriliyor", availabilityDetail: "Harici kişisel side effect'ler varsayılan factory izni değil, ayrı yönetilen yeteneklerdir." },
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
        <div className="factory-detail-top"><div><span className="micro-label">{factory.label}</span><h3>{factory.result}</h3><div className="factory-status-row"><span className={`availability-chip is-${factory.availability}`}>{factory.availabilityLabel}</span><small>{factory.availabilityDetail}</small></div></div><Link className="text-link" href={factory.href}>{c.open} →</Link></div>
        <div className="factory-pipeline"><span>{c.pipeline}</span><ol>{factory.pipeline.map((step, index) => <li key={step}><small>{String(index + 1).padStart(2, "0")}</small><strong>{step}</strong></li>)}</ol></div>
        <div className="factory-boundary"><span>{c.boundary}</span><p>{factory.boundary}</p></div>
      </div>
    </div>
  </div>;
}
