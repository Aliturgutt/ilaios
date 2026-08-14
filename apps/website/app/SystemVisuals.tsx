type Locale = "en" | "tr";
type Variant = "execution" | "planes" | "factory" | "trust" | "all";

const copy = {
  en: {
    execution: {
      label: "Governed execution",
      title: "One goal crosses explicit authority and acceptance boundaries.",
      text: "The product keeps planning, policy, routing, execution, validation and evidence visible as one governed chain.",
      nodes: [
        ["Goal", "Authenticated intent"],
        ["Policy", "Authority boundary"],
        ["Router", "Capability decision"],
        ["Factory", "Bounded workflow"],
        ["Validation", "Acceptance checks"],
        ["Evidence", "Reviewable proof"],
        ["Result", "Accepted outcome"],
      ],
    },
    planes: {
      label: "Control / execution separation",
      title: "Authority stays above replaceable execution resources.",
      text: "Clients, models and providers can change without becoming the source of policy, state or evidence truth.",
      control: [
        ["Identity & tenant", "Who is acting and under which boundary"],
        ["Policy & approvals", "What is allowed, denied or requires human authority"],
        ["Planning & orchestration", "How admitted work is decomposed and coordinated"],
        ["State & recovery", "What is durable, resumable and bounded"],
      ],
      executionPlane: [
        ["Factory orchestration", "Domain workflow / DAG"],
        ["Skills & tools", "Minimum required capability scope"],
        ["Models & providers", "Replaceable execution resources"],
        ["Validation & evidence", "Proof linked to the exact result"],
      ],
    },
    factory: {
      label: "Factory lifecycle",
      title: "Factories are bounded production paths, not parallel runtimes.",
      text: "Every native factory uses the same authority, routing, validation, evidence and recovery model while specializing the domain workflow.",
      steps: ["Request", "Scope", "Decompose", "Execute", "Validate", "Deliver"],
    },
    trust: {
      label: "Trust boundary",
      title: "Capability is never treated as permission.",
      text: "A request becomes an accepted side effect only after authority, constraints, validation and evidence are satisfied.",
      client: ["Client / user", "Request · approve · observe"],
      core: ["Authoritative control plane", "Identity · policy · scope · approvals"],
      sideEffect: ["External side effect", "Only after validation and acceptance"],
    },
  },
  tr: {
    execution: {
      label: "Yönetilen yürütme",
      title: "Tek hedef, açık yetki ve kabul sınırlarından geçer.",
      text: "Planlama, politika, yönlendirme, yürütme, doğrulama ve kanıt tek bir yönetilen zincir olarak görünür tutulur.",
      nodes: [
        ["Hedef", "Kimliği doğrulanmış niyet"],
        ["Politika", "Yetki sınırı"],
        ["Yönlendirme", "Yetenek kararı"],
        ["Üretim", "Sınırlandırılmış iş akışı"],
        ["Doğrulama", "Kabul kontrolleri"],
        ["Kanıt", "İncelenebilir kanıt"],
        ["Sonuç", "Kabul edilmiş çıktı"],
      ],
    },
    planes: {
      label: "Kontrol / yürütme ayrımı",
      title: "Yetki, değiştirilebilir yürütme kaynaklarının üzerinde kalır.",
      text: "İstemciler, modeller ve sağlayıcılar değişebilir; politika, durum veya kanıt gerçeğinin kaynağına dönüşmez.",
      control: [
        ["Kimlik ve tenant", "Kimin, hangi sınır içinde işlem yaptığı"],
        ["Politika ve onay", "Neye izin verildiği, neyin durduğu ve insan onayı"],
        ["Planlama ve orkestrasyon", "Kabul edilmiş işin nasıl ayrıştırılıp koordine edildiği"],
        ["Durum ve kurtarma", "Neyin kalıcı, devam ettirilebilir ve sınırlandırılmış olduğu"],
      ],
      executionPlane: [
        ["Factory orkestrasyonu", "Alan iş akışı / DAG"],
        ["Skill ve araçlar", "Gereken en düşük yetenek kapsamı"],
        ["Model ve sağlayıcılar", "Değiştirilebilir yürütme kaynakları"],
        ["Doğrulama ve kanıt", "Kesin sonuç sürümüne bağlı kanıt"],
      ],
    },
    factory: {
      label: "Factory yaşam döngüsü",
      title: "Factory'ler paralel runtime değil, sınırlandırılmış üretim yollarıdır.",
      text: "Her yerleşik factory aynı yetki, yönlendirme, doğrulama, kanıt ve kurtarma modelini kullanır; yalnızca alan iş akışı uzmanlaşır.",
      steps: ["Talep", "Kapsam", "Ayrıştırma", "Yürütme", "Doğrulama", "Teslim"],
    },
    trust: {
      label: "Güven sınırı",
      title: "Yetenek hiçbir zaman izin olarak kabul edilmez.",
      text: "Bir talep; yetki, kısıtlar, doğrulama ve kanıt sağlanmadan kabul edilmiş dış etkiye dönüşmez.",
      client: ["İstemci / kullanıcı", "Talep · onay · gözlem"],
      core: ["Yetkili kontrol katmanı", "Kimlik · politika · kapsam · onaylar"],
      sideEffect: ["Dış sistem etkisi", "Yalnız doğrulama ve kabul sonrasında"],
    },
  },
} as const;

function ExecutionVisual({ locale }: { locale: Locale }) {
  const c = copy[locale].execution;
  return <article className="system-visual" data-visual-role="governed-execution-diagram">
    <header><div><span className="micro-label">{c.label}</span><h3>{c.title}</h3><p>{c.text}</p></div><span className="visual-badge">01 / 04</span></header>
    <div className="node-flow" aria-label={c.title}>{c.nodes.map(([title, detail], index) => <div key={title} className={`node ${index === 1 || index === 2 ? "is-authority" : ""} ${index === 5 ? "is-evidence" : ""}`}><strong>{title}</strong><small>{detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</div>)}</div>
  </article>;
}

function PlanesVisual({ locale }: { locale: Locale }) {
  const c = copy[locale].planes;
  return <article className="system-visual" data-visual-role="control-execution-plane-diagram">
    <header><div><span className="micro-label">{c.label}</span><h3>{c.title}</h3><p>{c.text}</p></div><span className="visual-badge">02 / 04</span></header>
    <div className="plane-visual">
      <div className="plane-column"><strong>{locale === "tr" ? "Kontrol katmanı" : "Control plane"}</strong>{c.control.map(([title, text]) => <div className="plane-box is-authority" key={title}><b>{title}</b><span>{text}</span></div>)}</div>
      <div className="plane-column"><strong>{locale === "tr" ? "Yürütme düzlemi" : "Execution plane"}</strong>{c.executionPlane.map(([title, text]) => <div className="plane-box" key={title}><b>{title}</b><span>{text}</span></div>)}</div>
    </div>
  </article>;
}

function FactoryVisual({ locale }: { locale: Locale }) {
  const c = copy[locale].factory;
  return <article className="system-visual" data-visual-role="factory-lifecycle-diagram">
    <header><div><span className="micro-label">{c.label}</span><h3>{c.title}</h3><p>{c.text}</p></div><span className="visual-badge">03 / 04</span></header>
    <div className="lifecycle-flow" aria-label={c.title}>{c.steps.map((step, index) => <div key={step}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step}</strong></div>)}</div>
  </article>;
}

function TrustVisual({ locale }: { locale: Locale }) {
  const c = copy[locale].trust;
  return <article className="system-visual" data-visual-role="trust-boundary-diagram">
    <header><div><span className="micro-label">{c.label}</span><h3>{c.title}</h3><p>{c.text}</p></div><span className="visual-badge">04 / 04</span></header>
    <div className="trust-visual" aria-label={c.title}>
      <div><strong>{c.client[0]}</strong><small>{c.client[1]}</small></div><i aria-hidden="true">→</i>
      <div className="is-core"><strong>{c.core[0]}</strong><small>{c.core[1]}</small></div><i aria-hidden="true">→</i>
      <div><strong>{c.sideEffect[0]}</strong><small>{c.sideEffect[1]}</small></div>
    </div>
  </article>;
}

export default function SystemVisuals({ locale, variant = "all" }: { locale: Locale; variant?: Variant }) {
  if (variant === "execution") return <div className="system-visuals"><ExecutionVisual locale={locale} /></div>;
  if (variant === "planes") return <div className="system-visuals"><PlanesVisual locale={locale} /></div>;
  if (variant === "factory") return <div className="system-visuals"><FactoryVisual locale={locale} /></div>;
  if (variant === "trust") return <div className="system-visuals"><TrustVisual locale={locale} /></div>;
  return <div className="system-visuals is-grid">
    <ExecutionVisual locale={locale} />
    <PlanesVisual locale={locale} />
    <FactoryVisual locale={locale} />
    <TrustVisual locale={locale} />
  </div>;
}
