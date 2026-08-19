import Link from "next/link";
import SpatialArchitecture from "./SpatialArchitecture";
import SystemVisuals from "./SystemVisuals";
import CanonicalSystemDetail from "./CanonicalSystemDetail";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Architecture",
    title: "One authoritative control plane. Multiple governed capabilities.",
    lead: "ILAIOS separates user experience, business workflow composition, intelligence, execution resources and provider choice from the backend authority that owns policy, state, validation, evidence and recovery.",
    operatingTitle: "The Enterprise Operating Layer is composition, not authority.",
    operatingText: "Executive intelligence, operations, finance/cost intelligence, growth, commerce and research can shape a business workflow above the canonical execution spine. They do not create a second Core, orchestrator, router, Policy Engine, Approval Engine, Tool Gateway or evidence authority.",
    flowTitle: "Intent moves through explicit boundaries; accepted state and evidence move back to the user.",
    layers: [["Clients", "Request and observe; never become runtime authority."], ["Business workflow composition", "Resolves business goals into research, intelligence, operations and production work without owning runtime authority."], ["Control plane", "Owns policy, tenant context, orchestration and durable state."], ["Policy & approvals", "Resolve permissions, budgets, risk and human authority."], ["Capability fabric", "Factories, skills and services receive bounded contracts."], ["Routing & providers", "Models and external tools remain replaceable resources."], ["Validation & evidence", "Checks, provenance and criteria determine acceptance."], ["Delivery & recovery", "Accepted outcomes deliver; unresolved work repairs, stops or escalates."]],
    executionVisualTitle: "The canonical execution spine is one chain, not a collection of independent agents.",
    executionVisualLead: "Business workflow composition and factory selection happen before worker/provider routing; material steps create evidence and state during execution rather than only at the end.",
    runtimeTitle: "Execution admission produces scoped authority before ONE RoutingDecision.",
    runtimeText: "Authority, tenant isolation, privacy/residency, DLP/secrets, tool scope, risk, quality and budget are eligibility boundaries. Providers never become a second routing brain.",
    knowledgeTitle: "Knowledge informs execution without becoming authority.",
    knowledgeText: "Authorized context, provenance and purpose-aware retrieval are part of the contract; RAG is a shared governed context plane, not another factory or decision authority.",
    recoveryTitle: "Checkpoint and repair preserve bounded autonomy across failure.",
    recoveryText: "Resume reloads durable state and revalidates current authority. Validation failures may repair only inside explicit attempt, cost and elapsed-time limits.",
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
    lead: "ILAIOS; kullanıcı deneyimini, iş workflow composition katmanını, akıllı yetenekleri, yürütme kaynaklarını ve sağlayıcı seçimini politika, durum, doğrulama, kanıt ve kurtarmanın sahibi olan backend yetkisinden ayırır.",
    operatingTitle: "Kurumsal Çalışma Katmanı composition katmanıdır; yetki katmanı değildir.",
    operatingText: "Yönetici zekâsı, operasyonlar, finans/maliyet zekâsı, büyüme, ticaret ve araştırma kanonik yürütme omurgasının üzerinde bir iş akışını şekillendirebilir. İkinci Core, orchestrator, router, Policy Engine, Approval Engine, Tool Gateway veya evidence authority oluşturmaz.",
    flowTitle: "Niyet açık sınırlar üzerinden ilerler; kabul edilmiş durum ve kanıt kullanıcıya geri döner.",
    layers: [["İstemciler", "Talep eder ve gözlemler; çalışma zamanı yetkisi olmaz."], ["İş workflow composition", "İş hedeflerini araştırma, zekâ, operasyon ve üretim işlerine çözümler; runtime yetkisinin sahibi olmaz."], ["Kontrol katmanı", "Politika, tenant bağlamı, orkestrasyon ve dayanıklı durumun sahibidir."], ["Politika ve onaylar", "İzinleri, bütçeleri, riski ve insan otoritesini çözer."], ["Yetenek dokusu", "Factory'ler, skill'ler ve servisler sınırlandırılmış sözleşme alır."], ["Yönlendirme ve sağlayıcılar", "Modeller ve dış araçlar değiştirilebilir kaynak olarak kalır."], ["Doğrulama ve kanıt", "Kontroller, kaynak kökeni ve ölçütler kabulü belirler."], ["Teslim ve kurtarma", "Kabul edilen sonuç teslim edilir; çözülemeyen iş düzeltilir, durur veya yükseltilir."]],
    executionVisualTitle: "Kanonik yürütme omurgası bağımsız ajanlar topluluğu değil, tek yönetilen zincirdir.",
    executionVisualLead: "İş workflow composition ve factory seçimi worker/sağlayıcı yönlendirmesinden önce gelir; önemli adımlar kanıtı ve durumu yalnız sonda değil yürütme sırasında üretir.",
    runtimeTitle: "Execution admission, TEK RoutingDecision öncesinde scoped yetki üretir.",
    runtimeText: "Yetki, tenant isolation, privacy/residency, DLP/secrets, araç kapsamı, risk, kalite ve bütçe eligibility sınırlarıdır. Sağlayıcılar ikinci bir routing beynine dönüşmez.",
    knowledgeTitle: "Bilgi yürütmeyi besler; yetkinin sahibi olmaz.",
    knowledgeText: "Yetkili bağlam, provenance ve amaç duyarlı retrieval sözleşmenin parçasıdır; RAG yeni bir factory veya karar yetkisi değil paylaşılan yönetilen bağlam düzlemidir.",
    recoveryTitle: "Checkpoint ve repair, hata sırasında bounded autonomy'yi korur.",
    recoveryText: "Resume dayanıklı durumu yükler ve güncel yetkiyi yeniden doğrular. Validation hataları yalnız açık deneme, maliyet ve süre sınırları içinde onarılabilir.",
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
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kurumsal çalışma katmanı" : "Enterprise operating layer"}</div><h2>{c.operatingTitle}</h2></div><p>{c.operatingText}</p></div></div></section>
    <section className="section"><div className="shell architecture-primary"><div><div className="eyebrow">{locale === "tr" ? "Yetki akışı" : "Authority flow"}</div><h2>{c.flowTitle}</h2><div className="architecture-layer-list">{c.layers.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div><SpatialArchitecture locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Kanonik yürütme" : "Canonical execution"}</div><h2>{c.executionVisualTitle}</h2></div><p>{c.executionVisualLead}</p></div><SystemVisuals locale={locale} variant="execution" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Execution admission + routing</div><h2>{c.runtimeTitle}</h2></div><p>{c.runtimeText}</p></div><CanonicalSystemDetail locale={locale} variant="runtime" /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Knowledge / RAG</div><h2>{c.knowledgeTitle}</h2></div><p>{c.knowledgeText}</p></div><CanonicalSystemDetail locale={locale} variant="knowledge" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Checkpoint / Resume / Repair</div><h2>{c.recoveryTitle}</h2></div><p>{c.recoveryText}</p></div><CanonicalSystemDetail locale={locale} variant="recovery" /></div></section>
    <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Güven sınırları" : "Trust boundaries"}</div><h2>{c.boundariesTitle}</h2></div></div><div className="boundary-ledger">{c.boundaries.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell compact-cta"><div><div className="eyebrow">{locale === "tr" ? "Sağlayıcı bağımsızlığı" : "Provider independence"}</div><h2>{c.providerTitle}</h2></div><div className="actions"><Link className="button" href={`${base}/core`}>{c.core}</Link><Link className="button secondary" href={`${base}/platform/control-plane`}>{c.control}</Link><Link className="text-link" href={`${base}/docs`}>{c.docs} →</Link></div></div></section>
  </>;
}
