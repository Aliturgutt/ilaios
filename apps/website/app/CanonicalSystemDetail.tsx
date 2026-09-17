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
      title: "Basit istem yüzeyi, sınırlandırılmış bir yürütme sözleşmesine dönüşür.",
      text: "Yürütme kabul edilebilir işe dönüşmeden önce kimlik, kiracı/proje bağlamı, kabul ölçütleri ve yetkili bağlam oluşturulur.",
      steps: ["Giriş yap", "Kiracı + proje", "Doğal dil hedefi", "Niyet + gereksinimler", "Kabul ölçütleri", "Yetkili bağlam", "Sınırlandırılmış plan / DAG", "Yetenek + üretim alanı", "Yürütme kabulü", "Gerekirse onay", "Otonom yürütme", "Bağımsız kabul"],
    },
    runtime: {
      label: "Kabul, yönlendirme ve yürütme",
      title: "Yetenek, yönlendirme optimizasyonundan önce yetki sınırlarından geçer.",
      text: "Güvenlik, gizlilik, yerleşim, araç kapsamı, risk, kalite ve bütçe görevi sınırlar; ardından tek yönlendirme kararı çalışan sınıfı, onaylı adaptör ve değiştirilebilir sağlayıcıyı seçer.",
      admission: ["Yetki", "Kiracı izolasyonu", "Gizlilik / yerleşim", "Veri kaybı önleme / gizli bilgiler", "Araç izni", "Risk", "Kalite tabanı", "Bütçe / kota"],
      execution: ["Yürütme izni", "Tek yönlendirme kararı", "Kuyruk / zamanlayıcı", "Çalışan kiralaması + çitleme", "Çalışan", "Onaylı beceri", "Araç / sağlayıcı adaptörü", "Adım sonucu"],
    },
    knowledge: {
      label: "Yetkili bilgi katmanı",
      title: "Bilgi üretim alanlarını besler; üretim alanı veya yetki kaynağına dönüşmez.",
      text: "Bilgi getirme; kullanıcı, kiracı, proje ve amaca göre yetkilendirilir; dönen her bilgi birimi kaynak kökenini korur ve kiracılar arası sızıntı reddedilir.",
      steps: ["Yetkili kaynak", "İçe al + normalleştir", "Sınıflandırma + kaynak kökeni", "Dizin / grafik", "Yetki filtresi", "Getir + yeniden sırala", "Bağlam birleştirme", "Kaynak temelli sentez", "Atıf / kanıt"],
    },
    recovery: {
      label: "Kontrol noktası, doğrulama ve sınırlı onarım",
      title: "Hatalar güvenli şekilde devam eder veya durur; sonsuz otonomiye dönüşmez.",
      text: "Kontrol noktası; çıktı, kanıt, bütçe/yeniden deneme durumu ile rota/bağlam referanslarını korur. Devam etme güncel yetkiyi yeniden doğrular. Doğrulama hataları sınırlı onarım ve bağımsız yeniden değerlendirmeye girer.",
      checkpoint: ["Durumu kaydet", "Çıktı referansları", "Kanıt konumu", "Bütçe / yeniden deneme", "Kontrol noktası", "Yükle", "Yetkiyi yeniden doğrula", "Geçerli adımdan devam"],
      repair: ["Doğrulama BAŞARISIZ", "Hatayı sınıflandır", "Onarım önerisi", "Bütçe / deneme kontrolü", "Yeniden kabul", "Onarımı yürüt", "Yeniden değerlendir", "Kabul et veya dur"],
    },
    cost: {
      label: "Yönlendirmede maliyet yönetimi",
      title: "Düşük maliyet yalnız uygun kalite ve politika kümesi içinde optimize edilir.",
      text: "Güvenlik ve gizlilik uygunluğu maliyetten önce gelir. Bütçe katı bir kabul kısıtı olabilir; yeniden deneme ve onarım aynı yönetilen zarfı tüketir.",
      steps: ["Bütçe zarfı", "Politika / yetki", "Uygun kaynaklar", "Kalite tabanı", "Maliyet değerlendirmesi", "Gecikme / güvenilirlik", "Yönlendirme kararı", "Kullanım kaydı", "Maliyet eşleştirme", "Bütçe kanıtı"],
    },
    maturity: {
      label: "Yetenek gerçeklik modeli",
      title: "Kayıtlı veya dokümante edilmiş olmak üretime hazır olmak değildir.",
      text: "Kamuya açık ürün dili; kanonik yönü, gözlemlenen uygulama, test, sürekli entegrasyon, çalışma zamanı ve dağıtım kanıtından ayrı tutar.",
      steps: ["TASARLANDI", "TANIMLANDI", "UYGULANDI", "TEST EDİLDİ", "DOĞRULANDI", "DAĞITILDI / ÜRETİM"],
    },
    web: {
      label: "Web üretim alanı tam yaşam döngüsü",
      title: "Bitmiş web sitesi, tek bir üretim olayı değil; üretim zinciri ve kanıttır.",
      text: "Kanonik Web üretim alanı hedefi; araştırma, tasarım, uygulama, tarayıcı ve kalite kapıları, sınırlı onarım ve dağıtım doğrulaması üzerinden taşır.",
      steps: ["Web sitesi hedefi", "Araştırma", "Bilgi mimarisi", "Metin", "Tasarım sistemi", "Görsel tasarım", "Uygulama", "Tarayıcı kalite kontrolü", "Güvenlik kalite kontrolü", "Erişilebilirlik", "Performans", "SEO", "Görsel kalite kontrolü", "Kabul", "Sınırlı onarım", "Dağıtım doğrulaması", "Bitmiş site + kanıt"],
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
    runtime: <Panel key="runtime" label={c.runtime.label} title={c.runtime.title} text={c.runtime.text} role="admission-routing-runtime"><div className="canonical-dual"><div><span>{locale === "tr" ? "Kabul filtresi" : "Admission filter"}</span><Linear items={c.runtime.admission} /></div><div><span>{locale === "tr" ? "Yürütme zinciri" : "Execution chain"}</span><Linear items={c.runtime.execution} /></div></div></Panel>,
    knowledge: <Panel key="knowledge" label={c.knowledge.label} title={c.knowledge.title} text={c.knowledge.text} role="authorized-knowledge-plane"><Linear items={c.knowledge.steps} /></Panel>,
    recovery: <Panel key="recovery" label={c.recovery.label} title={c.recovery.title} text={c.recovery.text} role="checkpoint-bounded-repair"><div className="canonical-dual"><div><span>{locale === "tr" ? "Kontrol noktası / Devam" : "Checkpoint / Resume"}</span><Linear items={c.recovery.checkpoint} /></div><div><span>{locale === "tr" ? "Doğrulama / Onarım" : "Validation / Repair"}</span><Linear items={c.recovery.repair} /></div></div></Panel>,
    cost: <Panel key="cost" label={c.cost.label} title={c.cost.title} text={c.cost.text} role="finops-routing-flow"><Linear items={c.cost.steps} /></Panel>,
    maturity: <Panel key="maturity" label={c.maturity.label} title={c.maturity.title} text={c.maturity.text} role="capability-maturity-model"><Linear items={c.maturity.steps} /></Panel>,
    web: <Panel key="web" label={c.web.label} title={c.web.title} text={c.web.text} role="web-factory-full-lifecycle"><Linear items={c.web.steps} /></Panel>,
  } as const;
  if (variant !== "all") return <div className="canonical-detail-grid">{blocks[variant]}</div>;
  return <div className="canonical-detail-grid">{blocks.journey}{blocks.runtime}{blocks.knowledge}{blocks.recovery}{blocks.cost}{blocks.maturity}</div>;
}
