type Locale = "en" | "tr";
type Variant = "journey" | "runtime" | "knowledge" | "recovery" | "cost" | "maturity" | "web" | "all";

const copy = {
  en: {
    journey: {
      label: "Canonical request chain",
      title: "The simple prompt surface resolves into a bounded execution contract.",
      text: "Identity, tenant/project context, acceptance criteria and authorized context exist before execution is treated as admissible work.",
      steps: ["Sign in", "Tenant + project", "Natural-language goal", "Intent + requirements", "Acceptance criteria", "Authorized context", "Bounded plan / DAG", "Capability + factory", "Execution admission", "Approval if required", "Autonomous work", "Independent acceptance"],
    },
    runtime: {
      label: "Admission, routing and execution",
      title: "Capability is filtered by authority before routing optimizes execution.",
      text: "Security, privacy, residency, tool scope, risk, quality and budget constrain the task before ONE RoutingDecision selects a worker class, approved adapter and replaceable provider.",
      admission: ["Authority", "Tenant isolation", "Privacy / residency", "DLP / secrets", "Tool permission", "Risk", "Quality floor", "Budget / quota"],
      execution: ["ExecutionGrant", "ONE RoutingDecision", "Queue / scheduler", "Worker lease + fencing", "Worker", "Approved skill", "Tool / provider adapter", "Step result"],
    },
    knowledge: {
      label: "Authorized knowledge plane",
      title: "Knowledge informs factories without becoming a factory or an authority source.",
      text: "Retrieval is principal-, tenant-, project- and purpose-aware; every returned unit retains provenance and cross-tenant leakage is denied.",
      steps: ["Authorized source", "Ingest + normalize", "Classification + provenance", "Index / graph", "Authorization-aware filter", "Retrieve + rerank", "Context assembly", "Grounded synthesis", "Citations / evidence"],
    },
    recovery: {
      label: "Checkpoint, validation and bounded repair",
      title: "Failures resume safely or stop; they do not create infinite autonomy.",
      text: "Checkpoint state retains artifacts, evidence, budget/retry state and route/context references. Resume revalidates current authority. Validation failures enter bounded repair and independent re-evaluation.",
      checkpoint: ["Persist state", "Artifact refs", "Evidence cursor", "Budget / retry state", "Checkpoint", "Reload", "Revalidate authority", "Resume valid node"],
      repair: ["Validation FAIL", "Classify failure", "Repair proposal", "Budget / attempt check", "Re-admission", "Repair execution", "Re-evaluation", "Accept or stop"],
    },
    cost: {
      label: "FinOps inside routing",
      title: "Low cost is optimized only inside the eligible quality and policy set.",
      text: "Security and privacy eligibility come before cost. Budget can be a hard admission constraint; retries and repairs consume the same governed envelope.",
      steps: ["Budget envelope", "Policy / authorization", "Eligible resources", "Quality floor", "Cost evaluation", "Latency / reliability", "RoutingDecision", "Usage capture", "Cost attribution", "Budget evidence"],
    },
    maturity: {
      label: "Capability truth model",
      title: "Registered or documented does not mean production-ready.",
      text: "Public product language must keep canonical direction separate from observed implementation, tests, CI, runtime and deployment evidence.",
      steps: ["DESIGNED", "SPECIFIED", "IMPLEMENTED", "TESTED", "VERIFIED", "DEPLOYED / PRODUCTION"],
    },
    web: {
      label: "Web Factory complete lifecycle",
      title: "A finished website is a production sequence plus evidence, not a generation event.",
      text: "The canonical Web Factory carries the goal through research, design, implementation, browser and quality gates, bounded repair and deployment validation.",
      steps: ["Website goal", "Research", "Information architecture", "Copy", "Design system", "Visual design", "Implementation", "Browser QA", "Security QA", "Accessibility", "Performance", "SEO", "Visual QA", "Acceptance", "Bounded repair", "Deployment validation", "Finished website + evidence"],
    },
  },
  tr: {
    journey: {
      label: "Kanonik istek zinciri",
      title: "Basit prompt yüzeyi, sınırlandırılmış bir yürütme sözleşmesine dönüşür.",
      text: "Yürütme kabul edilebilir işe dönüşmeden önce kimlik, tenant/proje bağlamı, kabul ölçütleri ve yetkili bağlam oluşturulur.",
      steps: ["Giriş yap", "Tenant + proje", "Doğal dil hedefi", "Niyet + gereksinimler", "Kabul ölçütleri", "Yetkili bağlam", "Sınırlandırılmış plan / DAG", "Yetenek + factory", "Execution admission", "Gerekirse onay", "Otonom yürütme", "Bağımsız kabul"],
    },
    runtime: {
      label: "Admission, routing ve yürütme",
      title: "Yetenek, routing optimizasyonundan önce yetki sınırlarından geçer.",
      text: "Güvenlik, gizlilik, residency, araç kapsamı, risk, kalite ve bütçe görevi sınırlar; ardından TEK RoutingDecision worker sınıfı, onaylı adapter ve değiştirilebilir sağlayıcıyı seçer.",
      admission: ["Yetki", "Tenant isolation", "Gizlilik / residency", "DLP / secrets", "Araç izni", "Risk", "Kalite tabanı", "Bütçe / kota"],
      execution: ["ExecutionGrant", "TEK RoutingDecision", "Queue / scheduler", "Worker lease + fencing", "Worker", "Onaylı skill", "Tool / provider adapter", "Adım sonucu"],
    },
    knowledge: {
      label: "Yetkili knowledge plane",
      title: "Bilgi factory'leri besler; factory veya yetki kaynağına dönüşmez.",
      text: "Retrieval; principal, tenant, proje ve amaca göre yetkilendirilir; dönen her bilgi birimi kaynak kökenini korur ve tenant'lar arası sızıntı reddedilir.",
      steps: ["Yetkili kaynak", "Ingest + normalize", "Sınıflandırma + provenance", "Index / graph", "Yetki filtresi", "Retrieve + rerank", "Bağlam birleştirme", "Grounded synthesis", "Atıf / kanıt"],
    },
    recovery: {
      label: "Checkpoint, doğrulama ve bounded repair",
      title: "Hatalar güvenli şekilde devam eder veya durur; sonsuz otonomiye dönüşmez.",
      text: "Checkpoint; artifact, evidence, bütçe/retry durumu ile route/context referanslarını korur. Resume güncel yetkiyi yeniden doğrular. Validation hataları bounded repair ve bağımsız yeniden değerlendirmeye girer.",
      checkpoint: ["Durumu kaydet", "Artifact refs", "Evidence cursor", "Bütçe / retry", "Checkpoint", "Yükle", "Yetkiyi yeniden doğrula", "Geçerli node'dan devam"],
      repair: ["Validation FAIL", "Hatayı sınıflandır", "Repair proposal", "Bütçe / deneme kontrolü", "Re-admission", "Repair execution", "Re-evaluation", "Kabul et veya dur"],
    },
    cost: {
      label: "Routing içinde FinOps",
      title: "Düşük maliyet yalnız uygun kalite ve politika kümesi içinde optimize edilir.",
      text: "Güvenlik ve gizlilik uygunluğu maliyetten önce gelir. Bütçe hard admission kısıtı olabilir; retry ve repair aynı yönetilen zarfı tüketir.",
      steps: ["Bütçe zarfı", "Politika / yetki", "Uygun kaynaklar", "Kalite tabanı", "Maliyet değerlendirmesi", "Gecikme / güvenilirlik", "RoutingDecision", "Kullanım kaydı", "Maliyet eşleştirme", "Bütçe kanıtı"],
    },
    maturity: {
      label: "Yetenek gerçeklik modeli",
      title: "Kayıtlı veya dokümante edilmiş olmak production-ready olmak değildir.",
      text: "Kamuya açık ürün dili; kanonik yönü, gözlemlenen implementation, test, CI, runtime ve deployment kanıtından ayrı tutar.",
      steps: ["DESIGNED", "SPECIFIED", "IMPLEMENTED", "TESTED", "VERIFIED", "DEPLOYED / PRODUCTION"],
    },
    web: {
      label: "Web Factory tam yaşam döngüsü",
      title: "Bitmiş web sitesi, tek bir üretim olayı değil; üretim zinciri ve kanıttır.",
      text: "Kanonik Web Factory hedefi; araştırma, tasarım, implementation, browser/quality gate'leri, bounded repair ve deployment validation üzerinden taşır.",
      steps: ["Web sitesi hedefi", "Araştırma", "Bilgi mimarisi", "Metin", "Design system", "Görsel tasarım", "Implementation", "Browser QA", "Security QA", "Accessibility", "Performance", "SEO", "Visual QA", "Acceptance", "Bounded repair", "Deployment validation", "Bitmiş site + kanıt"],
    },
  },
} as const;

function Linear({ items }: { items: readonly string[] }) {
  return <div className="canonical-linear">{items.map((item, index) => <div key={`${item}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong>{index < items.length - 1 && <i aria-hidden="true">→</i>}</div>)}</div>;
}

function Panel({ label, title, text, children, role }: { label: string; title: string; text: string; children: React.ReactNode; role: string }) {
  return <article className="canonical-detail-panel" data-visual-role={role}><header><div><span className="micro-label">{label}</span><h3>{title}</h3><p>{text}</p></div></header>{children}</article>;
}

export default function CanonicalSystemDetail({ locale, variant = "all" }: { locale: Locale; variant?: Variant }) {
  const c = copy[locale];
  const blocks = {
    journey: <Panel key="journey" label={c.journey.label} title={c.journey.title} text={c.journey.text} role="canonical-request-chain"><Linear items={c.journey.steps} /></Panel>,
    runtime: <Panel key="runtime" label={c.runtime.label} title={c.runtime.title} text={c.runtime.text} role="admission-routing-runtime"><div className="canonical-dual"><div><span>{locale === "tr" ? "Admission filtresi" : "Admission filter"}</span><Linear items={c.runtime.admission} /></div><div><span>{locale === "tr" ? "Yürütme zinciri" : "Execution chain"}</span><Linear items={c.runtime.execution} /></div></div></Panel>,
    knowledge: <Panel key="knowledge" label={c.knowledge.label} title={c.knowledge.title} text={c.knowledge.text} role="authorized-knowledge-plane"><Linear items={c.knowledge.steps} /></Panel>,
    recovery: <Panel key="recovery" label={c.recovery.label} title={c.recovery.title} text={c.recovery.text} role="checkpoint-bounded-repair"><div className="canonical-dual"><div><span>Checkpoint / Resume</span><Linear items={c.recovery.checkpoint} /></div><div><span>Validation / Repair</span><Linear items={c.recovery.repair} /></div></div></Panel>,
    cost: <Panel key="cost" label={c.cost.label} title={c.cost.title} text={c.cost.text} role="finops-routing-flow"><Linear items={c.cost.steps} /></Panel>,
    maturity: <Panel key="maturity" label={c.maturity.label} title={c.maturity.title} text={c.maturity.text} role="capability-maturity-model"><Linear items={c.maturity.steps} /></Panel>,
    web: <Panel key="web" label={c.web.label} title={c.web.title} text={c.web.text} role="web-factory-full-lifecycle"><Linear items={c.web.steps} /></Panel>,
  } as const;
  if (variant !== "all") return <div className="canonical-detail-grid">{blocks[variant]}</div>;
  return <div className="canonical-detail-grid">{blocks.journey}{blocks.runtime}{blocks.knowledge}{blocks.recovery}{blocks.cost}{blocks.maturity}</div>;
}
