"use client";

import { useState } from "react";

type Locale = "en" | "tr";
type Variant = "execution" | "planes" | "factory" | "trust" | "all";
type Detail = { label: string; title: string; description: string } | null;

const copy = {
  en: {
    instruction: "Select an element to inspect its role in the governed workflow.",
    execution: {
      label: "Governed execution",
      title: "One goal crosses explicit authority and acceptance boundaries.",
      text: "The product keeps planning, policy, routing, execution, validation and evidence visible as one governed chain.",
      nodes: [
        ["Goal", "Authenticated intent", "Captures the signed-in user's requested outcome, tenant/project context and acceptance criteria without granting additional authority."],
        ["Policy", "Authority boundary", "Applies identity, permissions, privacy, tool scope, risk, approvals and budget limits before work is admitted."],
        ["Router", "Capability decision", "Chooses an eligible capability, model, tool or provider inside the admitted scope without widening permissions."],
        ["Factory", "Bounded workflow", "Runs the approved domain workflow through the appropriate native factory and governed execution path."],
        ["Validation", "Acceptance checks", "Runs deterministic checks, security gates and explicit acceptance criteria before an output can advance."],
        ["Evidence", "Reviewable proof", "Preserves validation results, provenance and execution lineage so material outcomes remain inspectable and attributable."],
        ["Result", "Accepted outcome", "Represents the finished product only after required acceptance gates pass and the result is linked to its evidence."],
      ],
    },
    planes: {
      label: "Control / execution separation",
      title: "Authority stays above replaceable execution resources.",
      text: "Clients, models and providers can change without becoming the source of policy, state or evidence truth.",
      control: [
        ["Identity & tenant", "Who is acting and under which boundary", "Establishes the authenticated principal, tenant and project boundary that all later work must preserve."],
        ["Policy & approvals", "What is allowed, denied or requires human authority", "Decides whether work may proceed, must stop, or needs explicit approval before side effects are possible."],
        ["Planning & orchestration", "How admitted work is decomposed and coordinated", "Turns accepted work into bounded steps and coordinates the execution path without becoming a second authority plane."],
        ["State & recovery", "What is durable, resumable and bounded", "Keeps checkpoints, resumable state and repair limits explicit so failure cannot become infinite autonomous looping."],
      ],
      executionPlane: [
        ["Factory orchestration", "Domain workflow / DAG", "Executes the selected domain production path using the admitted plan and acceptance contract."],
        ["Skills & tools", "Minimum required capability scope", "Uses only the capabilities required for the accepted work and keeps tool scope bounded."],
        ["Models & providers", "Replaceable execution resources", "Supplies reasoning or generation capacity while remaining replaceable and subordinate to platform authority."],
        ["Validation & evidence", "Proof linked to the exact result", "Checks the produced artifact and binds reviewable evidence to the exact accepted outcome."],
      ],
    },
    factory: {
      label: "Factory lifecycle",
      title: "Factories are bounded production paths, not parallel runtimes.",
      text: "Every native factory uses the same authority, routing, validation, evidence and recovery model while specializing the domain workflow.",
      steps: [
        ["Request", "Capture the outcome and the user's explicit acceptance intent."],
        ["Scope", "Resolve authorized context, constraints, risk and the minimum work boundary."],
        ["Decompose", "Create bounded work units and dependencies that can be executed and checked."],
        ["Execute", "Run the selected factory path with only admitted skills, tools and providers."],
        ["Validate", "Apply deterministic checks, security gates and acceptance criteria to the artifact."],
        ["Deliver", "Return the accepted result with evidence; unresolved work stops or enters bounded repair."],
      ],
    },
    trust: {
      label: "Trust boundary",
      title: "Capability is never treated as permission.",
      text: "A request becomes an accepted side effect only after authority, constraints, validation and evidence are satisfied.",
      nodes: [
        ["Client / user", "Request · approve · observe", "The user expresses the goal, supplies permitted context and provides approval only where the workflow requires it."],
        ["Authoritative control plane", "Identity · policy · scope · approvals", "The platform remains the authority for permissions, policy, execution admission, state and acceptance boundaries."],
        ["External side effect", "Only after validation and acceptance", "Publishing, mutation or other external effects occur only inside admitted authority and after required gates are satisfied."],
      ],
    },
  },
  tr: {
    instruction: "Yönetilen akıştaki rolünü görmek için bir öğe seçin.",
    execution: {
      label: "Yönetilen yürütme",
      title: "Tek hedef, açık yetki ve kabul sınırlarından geçer.",
      text: "Planlama, politika, yönlendirme, yürütme, doğrulama ve kanıt tek bir yönetilen zincir olarak görünür tutulur.",
      nodes: [
        ["Hedef", "Kimliği doğrulanmış niyet", "Oturum açmış kullanıcının istediği sonucu, tenant/proje bağlamını ve kabul kriterlerini alır; kendi kendine ek yetki üretmez."],
        ["Politika", "Yetki sınırı", "İş kabul edilmeden önce kimlik, izinler, gizlilik, araç kapsamı, risk, onay ve bütçe sınırlarını uygular."],
        ["Yönlendirme", "Yetenek kararı", "Kabul edilmiş kapsam içinde uygun yetenek, model, araç veya sağlayıcıyı seçer; izinleri genişletemez."],
        ["Üretim", "Sınırlandırılmış iş akışı", "Onaylı alan akışını uygun yerleşik factory ve yönetilen yürütme yolu üzerinden çalıştırır."],
        ["Doğrulama", "Kabul kontrolleri", "Bir çıktının ilerlemesi için deterministik kontrolleri, güvenlik kapılarını ve açık kabul kriterlerini uygular."],
        ["Kanıt", "İncelenebilir kanıt", "Doğrulama sonuçlarını, provenance bilgisini ve yürütme soyunu koruyarak sonucu incelenebilir ve eşleştirilebilir tutar."],
        ["Sonuç", "Kabul edilmiş çıktı", "Yalnız gerekli kabul kapıları geçildikten ve kanıt sonuçla eşleştirildikten sonra bitmiş ürünü temsil eder."],
      ],
    },
    planes: {
      label: "Kontrol / yürütme ayrımı",
      title: "Yetki, değiştirilebilir yürütme kaynaklarının üzerinde kalır.",
      text: "İstemciler, modeller ve sağlayıcılar değişebilir; politika, durum veya kanıt gerçeğinin kaynağına dönüşmez.",
      control: [
        ["Kimlik ve tenant", "Kimin, hangi sınır içinde işlem yaptığı", "Kimliği doğrulanmış principal, tenant ve proje sınırını kurar; sonraki tüm iş bu sınırı korur."],
        ["Politika ve onay", "Neye izin verildiği, neyin durduğu ve insan onayı", "İşin ilerleyip ilerleyemeyeceğine, durması gerekip gerekmediğine veya açık onay isteyip istemediğine karar verir."],
        ["Planlama ve orkestrasyon", "Kabul edilmiş işin nasıl ayrıştırılıp koordine edildiği", "Kabul edilen işi sınırlandırılmış adımlara dönüştürür ve yürütme yolunu ikinci bir yetki düzlemi oluşturmadan koordine eder."],
        ["Durum ve kurtarma", "Neyin kalıcı, devam ettirilebilir ve sınırlandırılmış olduğu", "Checkpoint, devam ettirilebilir durum ve repair sınırlarını açık tutarak sonsuz otonom döngüyü engeller."],
      ],
      executionPlane: [
        ["Factory orkestrasyonu", "Alan iş akışı / DAG", "Kabul edilmiş planı ve acceptance contract'ı kullanarak seçilen alan üretim yolunu yürütür."],
        ["Skill ve araçlar", "Gereken en düşük yetenek kapsamı", "Yalnız kabul edilmiş iş için gereken yetenekleri kullanır ve araç kapsamını sınırlandırılmış tutar."],
        ["Model ve sağlayıcılar", "Değiştirilebilir yürütme kaynakları", "Reasoning veya generation kapasitesi sağlar; ancak platform yetkisinin altında ve değiştirilebilir kalır."],
        ["Doğrulama ve kanıt", "Kesin sonuç sürümüne bağlı kanıt", "Üretilen artifact'i kontrol eder ve incelenebilir kanıtı kesin kabul edilmiş sonuçla eşleştirir."],
      ],
    },
    factory: {
      label: "Factory yaşam döngüsü",
      title: "Factory'ler paralel runtime değil, sınırlandırılmış üretim yollarıdır.",
      text: "Her yerleşik factory aynı yetki, yönlendirme, doğrulama, kanıt ve kurtarma modelini kullanır; yalnızca alan iş akışı uzmanlaşır.",
      steps: [
        ["Talep", "İstenen sonucu ve kullanıcının açık kabul niyetini alır."],
        ["Kapsam", "Yetkili bağlamı, kısıtları, riski ve gereken en küçük iş sınırını çözer."],
        ["Ayrıştırma", "Yürütülebilir ve doğrulanabilir sınırlandırılmış iş birimleri ile bağımlılıkları oluşturur."],
        ["Yürütme", "Seçilen factory yolunu yalnız kabul edilmiş skill, araç ve sağlayıcılarla çalıştırır."],
        ["Doğrulama", "Artifact'e deterministik kontrolleri, güvenlik kapılarını ve kabul kriterlerini uygular."],
        ["Teslim", "Kabul edilmiş sonucu kanıtıyla döndürür; çözülemeyen iş durur veya bounded repair'e girer."],
      ],
    },
    trust: {
      label: "Güven sınırı",
      title: "Yetenek hiçbir zaman izin olarak kabul edilmez.",
      text: "Bir talep; yetki, kısıtlar, doğrulama ve kanıt sağlanmadan kabul edilmiş dış etkiye dönüşmez.",
      nodes: [
        ["İstemci / kullanıcı", "Talep · onay · gözlem", "Kullanıcı hedefi ifade eder, izin verilen bağlamı sağlar ve yalnız iş akışının gerektirdiği yerde onay verir."],
        ["Yetkili kontrol katmanı", "Kimlik · politika · kapsam · onaylar", "Platform izinler, politika, execution admission, durum ve kabul sınırlarının yetkili kaynağı olarak kalır."],
        ["Dış sistem etkisi", "Yalnız doğrulama ve kabul sonrasında", "Yayınlama, mutation veya diğer dış etkiler yalnız kabul edilmiş yetki içinde ve gerekli kapılar geçildikten sonra gerçekleşir."],
      ],
    },
  },
} as const;

function DetailPanel({ detail }: { detail: Detail }) {
  if (!detail) return null;
  return <div className="system-inline-detail" aria-live="polite">
    <span className="micro-label">{detail.label}</span>
    <strong>{detail.title}</strong>
    <p>{detail.description}</p>
  </div>;
}

function ExecutionVisual({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState(0);
  const selected = c.execution.nodes[active];
  return <article className="system-visual" data-visual-role="governed-execution-diagram">
    <header><div><span className="micro-label">{c.execution.label}</span><h3>{c.execution.title}</h3><p>{c.execution.text}</p></div><span className="visual-badge">01 / 04</span></header>
    <p className="system-visual-instruction">{c.instruction}</p>
    <div className="node-flow" aria-label={c.execution.title}>{c.execution.nodes.map(([title, detail], index) => <button type="button" key={title} className={`node system-visual-control${index === 1 || index === 2 ? " is-authority" : ""}${index === 5 ? " is-evidence" : ""}${active === index ? " is-active" : ""}`} aria-pressed={active === index} onClick={() => setActive(index)}><strong>{title}</strong><small>{detail}</small>{index < c.execution.nodes.length - 1 && <i aria-hidden="true" />}</button>)}</div>
    <DetailPanel detail={{ label: `${String(active + 1).padStart(2, "0")} · ${selected[0]}`, title: selected[1], description: selected[2] }} />
  </article>;
}

function PlanesVisual({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState("control-0");
  const [kind, indexText] = active.split("-");
  const index = Number(indexText);
  const selected = kind === "control" ? c.planes.control[index] : c.planes.executionPlane[index];
  const selectedLabel = kind === "control" ? (locale === "tr" ? "Kontrol katmanı" : "Control plane") : (locale === "tr" ? "Yürütme düzlemi" : "Execution plane");
  return <article className="system-visual" data-visual-role="control-execution-plane-diagram">
    <header><div><span className="micro-label">{c.planes.label}</span><h3>{c.planes.title}</h3><p>{c.planes.text}</p></div><span className="visual-badge">02 / 04</span></header>
    <p className="system-visual-instruction">{c.instruction}</p>
    <div className="plane-visual">
      <div className="plane-column"><strong>{locale === "tr" ? "Kontrol katmanı" : "Control plane"}</strong>{c.planes.control.map(([title, text], itemIndex) => <button type="button" className={`plane-box is-authority system-visual-control${active === `control-${itemIndex}` ? " is-active" : ""}`} key={title} aria-pressed={active === `control-${itemIndex}`} onClick={() => setActive(`control-${itemIndex}`)}><b>{title}</b><span>{text}</span></button>)}</div>
      <div className="plane-column"><strong>{locale === "tr" ? "Yürütme düzlemi" : "Execution plane"}</strong>{c.planes.executionPlane.map(([title, text], itemIndex) => <button type="button" className={`plane-box system-visual-control${active === `execution-${itemIndex}` ? " is-active" : ""}`} key={title} aria-pressed={active === `execution-${itemIndex}`} onClick={() => setActive(`execution-${itemIndex}`)}><b>{title}</b><span>{text}</span></button>)}</div>
    </div>
    <DetailPanel detail={{ label: selectedLabel, title: selected[0], description: selected[2] }} />
  </article>;
}

function FactoryVisual({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState(0);
  const selected = c.factory.steps[active];
  return <article className="system-visual" data-visual-role="factory-lifecycle-diagram">
    <header><div><span className="micro-label">{c.factory.label}</span><h3>{c.factory.title}</h3><p>{c.factory.text}</p></div><span className="visual-badge">03 / 04</span></header>
    <p className="system-visual-instruction">{c.instruction}</p>
    <div className="lifecycle-flow" aria-label={c.factory.title}>{c.factory.steps.map(([step], index) => <button type="button" key={step} className={`lifecycle-step system-visual-control${active === index ? " is-active" : ""}`} aria-pressed={active === index} onClick={() => setActive(index)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step}</strong></button>)}</div>
    <DetailPanel detail={{ label: `${String(active + 1).padStart(2, "0")} / ${String(c.factory.steps.length).padStart(2, "0")}`, title: selected[0], description: selected[1] }} />
  </article>;
}

function TrustVisual({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState(1);
  const selected = c.trust.nodes[active];
  return <article className="system-visual" data-visual-role="trust-boundary-diagram">
    <header><div><span className="micro-label">{c.trust.label}</span><h3>{c.trust.title}</h3><p>{c.trust.text}</p></div><span className="visual-badge">04 / 04</span></header>
    <p className="system-visual-instruction">{c.instruction}</p>
    <div className="trust-visual" aria-label={c.trust.title}>
      {c.trust.nodes.map(([title, summary], index) => <div className="trust-node-wrap" key={title}><button type="button" className={`trust-node system-visual-control${index === 1 ? " is-core" : ""}${active === index ? " is-active" : ""}`} aria-pressed={active === index} onClick={() => setActive(index)}><strong>{title}</strong><small>{summary}</small></button>{index < c.trust.nodes.length - 1 && <i aria-hidden="true">→</i>}</div>)}
    </div>
    <DetailPanel detail={{ label: `${String(active + 1).padStart(2, "0")} / 03`, title: selected[0], description: selected[2] }} />
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
