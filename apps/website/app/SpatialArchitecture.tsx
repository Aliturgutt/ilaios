"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type Locale = "en" | "tr";
type Tilt = { x: number; y: number };

type NodeCopy = {
  title: string;
  detail: string;
  description: string;
  href: string;
  source: string;
};

const copy: Record<Locale, { label: string; aria: string; hint: string; open: string; nodes: NodeCopy[] }> = {
  en: {
    label: "Governed execution map",
    aria: "ILAIOS governed execution architecture from goal through policy, routing, factory execution, validation, evidence and result",
    hint: "Select a stage to see its governed responsibility and follow the canonical architecture path.",
    open: "Open related architecture",
    nodes: [
      { title: "Goal", detail: "Authenticated intent", description: "Turns the authenticated request into GoalSpec, explicit requirements and acceptance criteria before execution begins.", href: "/architecture#request-execution", source: "GoalSpec · requirements · acceptance criteria" },
      { title: "Policy", detail: "Authority boundary", description: "Execution admission checks authorization, tenant isolation, privacy/residency, DLP/secrets, tool scope, budget and risk. Allowed work receives an ExecutionGrant.", href: "/security#policy-gateway", source: "PolicyDecision · ExecutionGrant" },
      { title: "Router", detail: "ONE RoutingDecision", description: "Selects one permitted execution resource after policy admission. Provider health, quality, cost and latency are inputs; they never override authority or privacy constraints.", href: "/architecture#routing", source: "ONE RoutingDecision · approved adapter" },
      { title: "Factory", detail: "Bounded execution", description: "A native factory coordinates domain work inside the approved scope. Factory orchestration does not create a second Core, policy authority, runtime or routing truth.", href: "/factories", source: "Factory orchestration · governed worker execution" },
      { title: "Validation", detail: "Acceptance checks", description: "Step outputs and the final artifact are checked against explicit acceptance criteria. Failure may enter bounded repair; policy and security failures are never repaired around.", href: "/architecture#validation", source: "Step validation · independent final evaluation" },
      { title: "Evidence", detail: "Reviewable proof", description: "Material steps preserve evidence, authoritative state, checkpoints and provenance so execution can be reviewed, resumed and audited without inventing a parallel truth.", href: "/security#evidence", source: "Evidence · checkpoint · provenance" },
      { title: "Result", detail: "Verified finished product", description: "Delivery or publication occurs only after required verification passes and any required final-action approval is satisfied.", href: "/architecture#request-execution", source: "AcceptanceManifest · delivery · verified result" },
    ],
  },
  tr: {
    label: "Yönetilen yürütme haritası",
    aria: "Hedeften politika, yönlendirme, üretim, doğrulama, kanıt ve doğrulanmış sonuca uzanan ILAIOS yönetilen yürütme mimarisi",
    hint: "Yönetilen sorumluluğunu görmek ve kanonik mimari yoluna gitmek için bir aşama seçin.",
    open: "İlgili mimariyi aç",
    nodes: [
      { title: "Hedef", detail: "Kimliği doğrulanmış niyet", description: "Kimliği doğrulanmış isteği yürütme başlamadan önce GoalSpec, açık gereksinimler ve kabul kriterlerine dönüştürür.", href: "/tr/architecture#request-execution", source: "GoalSpec · gereksinimler · kabul kriterleri" },
      { title: "Politika", detail: "Yetki sınırı", description: "Yürütme kabulü; yetki, tenant izolasyonu, gizlilik/residency, DLP/secrets, araç kapsamı, bütçe ve riski denetler. İzin verilen iş ExecutionGrant alır.", href: "/tr/security#policy-gateway", source: "PolicyDecision · ExecutionGrant" },
      { title: "Yönlendirici", detail: "TEK RoutingDecision", description: "Politika kabulünden sonra izinli yürütme kaynağını tek routing gerçeğiyle seçer. Sağlayıcı sağlık, kalite, maliyet ve gecikme girdidir; yetki veya gizlilik sınırlarını aşamaz.", href: "/tr/architecture#routing", source: "TEK RoutingDecision · onaylı adapter" },
      { title: "Üretim", detail: "Sınırlandırılmış yürütme", description: "Yerleşik factory, alan işini verilen kapsam içinde koordine eder. İkinci Core, politika otoritesi, runtime veya routing gerçeği oluşturamaz.", href: "/tr/factories", source: "Factory orkestrasyonu · yönetilen worker yürütmesi" },
      { title: "Doğrulama", detail: "Kabul kontrolleri", description: "Adım çıktıları ve final artifact açık kabul kriterlerine göre kontrol edilir. Başarısızlık bounded repair'e girebilir; politika ve güvenlik hatalarının etrafından dolaşılmaz.", href: "/tr/architecture#validation", source: "Adım doğrulama · bağımsız final değerlendirme" },
      { title: "Kanıt", detail: "İncelenebilir kanıt", description: "Önemli adımlar kanıtı, otoritatif durumu, checkpoint ve provenance bilgisini korur; böylece yürütme paralel bir gerçek oluşturmadan incelenebilir, sürdürülebilir ve denetlenebilir.", href: "/tr/security#evidence", source: "Kanıt · checkpoint · provenance" },
      { title: "Sonuç", detail: "Doğrulanmış bitmiş ürün", description: "Teslim veya yayın yalnızca gerekli doğrulama PASS olduğunda ve gerekiyorsa final eylem onayı karşılandığında gerçekleşir.", href: "/tr/architecture#request-execution", source: "AcceptanceManifest · teslim · doğrulanmış sonuç" },
    ],
  },
};

function applyStageTransform(stage: HTMLDivElement | null, tilt: Tilt, scrollDepth: number) {
  if (!stage) return;
  stage.style.transform = `perspective(900px) rotateX(${tilt.y + scrollDepth}deg) rotateY(${tilt.x}deg)`;
}

export default function SpatialArchitecture({ locale, compact = false }: { locale: Locale; compact?: boolean }) {
  const c = copy[locale];
  const [active, setActive] = useState(0);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const tiltRef = useRef<Tilt>({ x: 0, y: 0 });
  const scrollDepthRef = useRef(0);

  useEffect(() => {
    const update = () => {
      const wrapper = wrapperRef.current;
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!wrapper || window.innerWidth < 760 || reduced) {
        scrollDepthRef.current = 0;
        applyStageTransform(stageRef.current, tiltRef.current, 0);
        return;
      }
      const rect = wrapper.getBoundingClientRect();
      const viewportCenter = window.innerHeight / 2;
      const elementCenter = rect.top + rect.height / 2;
      const normalized = Math.max(-1, Math.min(1, (viewportCenter - elementCenter) / Math.max(window.innerHeight, 1)));
      scrollDepthRef.current = normalized * 1.6;
      applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, []);

  const selected = c.nodes[active];
  return <div ref={wrapperRef} className={`spatial-map ${compact ? "is-compact" : ""}`} data-visual-role="architecture-spatial-map">
    <div className="spatial-map-head"><span className="micro-label">{c.label}</span><small>{c.hint}</small></div>
    <div ref={stageRef} className="spatial-stage" role="group" aria-label={c.aria} style={{ transform: "perspective(900px) rotateX(0deg) rotateY(0deg)" }}
      onPointerMove={event => { const rect = event.currentTarget.getBoundingClientRect(); tiltRef.current = { x: ((event.clientX - rect.left) / rect.width - 0.5) * 4, y: -((event.clientY - rect.top) / rect.height - 0.5) * 3 }; applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current); }}
      onPointerLeave={() => { tiltRef.current = { x: 0, y: 0 }; applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current); }}>
      {c.nodes.map((node, index) => <button type="button" className={`spatial-node spatial-node-${index + 1}${active === index ? " is-active" : ""}`} key={node.title} onClick={() => setActive(index)} aria-pressed={active === index} aria-controls="spatial-map-detail"><span>{String(index + 1).padStart(2, "0")}</span><strong>{node.title}</strong><small>{node.detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</button>)}
    </div>
    <div id="spatial-map-detail" className="spatial-map-detail" aria-live="polite">
      <div><span className="micro-label">{selected.detail}</span><h3>{selected.title}</h3><p>{selected.description}</p><small>{selected.source}</small></div>
      <Link className="text-link" href={selected.href}>{c.open} →</Link>
    </div>
  </div>;
}
