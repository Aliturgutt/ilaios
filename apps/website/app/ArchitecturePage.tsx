import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Architecture",
    title: "One authoritative control plane. Multiple governed capabilities.",
    lead: "ILAIOS separates user experience, intelligence, execution resources and provider choice from the backend authority that owns policy, state, validation, evidence and recovery.",
    flowTitle: "Intent moves through explicit boundaries; accepted state and evidence move back to the user.",
    layers: [["Clients", "Request and observe; never become runtime authority."], ["Control plane", "Owns policy, tenant context, orchestration and durable state."], ["Policy & approvals", "Resolve permissions, budgets, risk and human authority."], ["Capability fabric", "Factories, skills and services receive bounded contracts."], ["Routing & providers", "Models and external tools remain replaceable resources."], ["Validation & evidence", "Checks, provenance and criteria determine acceptance."], ["Delivery & recovery", "Accepted outcomes deliver; unresolved work repairs, stops or escalates."]],
    knowledgeTitle: "Knowledge informs execution without becoming authority.",
    knowledgeText: "Authorized context → project memory → source provenance → tenant-aware retrieval → grounded synthesis → evidence.",
    boundariesTitle: "Capability is not permission.",
    boundaries: [["Authority", "Request ≠ permission."], ["Context", "Identity and purpose bound usable context."], ["Execution", "Capabilities receive minimum required scope."], ["Acceptance", "Generated output is not final until required checks pass."], ["Recovery", "Retry and repair are bounded."]],
    providerTitle: "ILAIOS remains the product brain while execution resources evolve.",
    core: "Explore Core",
    control: "Control plane",
    docs: "Documentation",
  },
  tr: {
    eyebrow: "Mimari",
    title: "Tek yetkili kontrol katmanı. Birden çok yönetilen yetenek.",
    lead: "ILAIOS; kullanıcı deneyimini, akıllı yetenekleri, yürütme kaynaklarını ve sağlayıcı seçimini politika, durum, doğrulama, kanıt ve kurtarmanın sahibi olan backend yetkisinden ayırır.",
    flowTitle: "Niyet açık sınırlar üzerinden ilerler; kabul edilmiş durum ve kanıt kullanıcıya geri döner.",
    layers: [["İstemciler", "Talep eder ve gözlemler; çalışma zamanı yetkisi olmaz."], ["Kontrol katmanı", "Politika, tenant bağlamı, orkestrasyon ve dayanıklı durumun sahibidir."], ["Politika ve onaylar", "İzinleri, bütçeleri, riski ve insan otoritesini çözer."], ["Yetenek dokusu", "Üretim alanları, skill'ler ve servisler sınırlandırılmış sözleşme alır."], ["Yönlendirme ve sağlayıcılar", "Modeller ve dış araçlar değiştirilebilir kaynak olarak kalır."], ["Doğrulama ve kanıt", "Kontroller, kaynak kökeni ve ölçütler kabulü belirler."], ["Teslim ve kurtarma", "Kabul edilen sonuç teslim edilir; çözülemeyen iş düzeltilir, durur veya yükseltilir."]],
    knowledgeTitle: "Bilgi yürütmeyi besler; yetkinin sahibi olmaz.",
    knowledgeText: "Yetkili bağlam → proje hafızası → kaynak kökeni → tenant-aware retrieval → grounded synthesis → kanıt.",
    boundariesTitle: "Yetenek, izin demek değildir.",
    boundaries: [["Yetki", "Talep ≠ izin."], ["Bağlam", "Kimlik ve amaç kullanılabilir bağlamı sınırlar."], ["Yürütme", "Yetenekler yalnız gereken en düşük kapsamı alır."], ["Kabul", "Gerekli kontroller geçmeden üretilen çıktı final değildir."], ["Kurtarma", "Yeniden deneme ve düzeltme sınırlandırılır."]],
    providerTitle: "Yürütme kaynakları değişirken ILAIOS ürün beyni olarak kalır.",
    core: "Core'u incele",
    control: "Kontrol katmanı",
    docs: "Dokümantasyon",
  },
} as const;

export default function ArchitecturePage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell architecture-primary"><div><div className="eyebrow">{locale === "tr" ? "Yetki akışı" : "Authority flow"}</div><h2>{c.flowTitle}</h2><div className="architecture-layer-list">{c.layers.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div><SpatialArchitecture locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell knowledge-band"><div><div className="eyebrow">Knowledge / RAG</div><h2>{c.knowledgeTitle}</h2></div><p>{c.knowledgeText}</p></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırları" : "Trust boundaries"}</div><h2>{c.boundariesTitle}</h2></div></div><div className="boundary-ledger">{c.boundaries.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{locale === "tr" ? "Sağlayıcı bağımsızlığı" : "Provider independence"}</div><h2>{c.providerTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/core`}>{c.core}</Link><Link className="button secondary" href={`${base}/platform/control-plane`}>{c.control}</Link><Link className="text-link" href={`${base}/docs`}>{c.docs} →</Link></div></div></section>
  </>;
}
