"use client";

import { useEffect, useRef, useState } from "react";

type Locale = "en" | "tr";
type Tilt = { x: number; y: number };
type Node = { title: string; detail: string; description: string };

const copy: Record<Locale, { label: string; aria: string; hint: string; nodes: Node[] }> = {
  en: {
    label: "Governed execution map",
    aria: "ILAIOS governed execution architecture from goal through policy, routing, factory execution, validation, evidence and result",
    hint: "Select a stage to see what it does and what it protects.",
    nodes: [
      { title: "Goal", detail: "Authenticated intent", description: "Turns the signed-in user's requested outcome, tenant/project context, acceptance criteria and authorized context into bounded work. The goal describes the outcome; it does not grant itself authority." },
      { title: "Policy", detail: "Authority boundary", description: "Applies identity, tenant isolation, permissions, privacy/residency, DLP/secrets, tool scope, risk, approval and budget boundaries before execution is admitted. Policy is authoritative; models are not." },
      { title: "Router", detail: "Capability selection", description: "Produces the single governed RoutingDecision that selects an eligible capability, model, tool or provider inside the admitted scope. Routing may optimize execution but cannot widen permissions." },
      { title: "Factory", detail: "Bounded execution", description: "Executes the approved bounded DAG through the appropriate native factory and governed worker/tool/provider path. Factories remain domain execution surfaces, not parallel control planes." },
      { title: "Validation", detail: "Acceptance checks", description: "Runs deterministic checks, security gates and explicit acceptance criteria before an output can advance. A generated artifact is not treated as finished merely because generation completed." },
      { title: "Evidence", detail: "Reviewable proof", description: "Preserves validation results, important events, provenance and execution lineage so the outcome can be reviewed, audited, recovered and explained without relying on model assertions." },
      { title: "Result", detail: "Accepted outcome", description: "Represents the finished product only after required acceptance gates pass. Delivery or external side effects occur within the authorized scope, with checkpoint/resume and bounded repair available where the workflow permits them." },
    ],
  },
  tr: {
    label: "Yönetilen yürütme haritası",
    aria: "Hedeften politika, yönlendirme, üretim, doğrulama, kanıt ve kabul edilmiş sonuca uzanan ILAIOS yönetilen yürütme mimarisi",
    hint: "Ne yaptığını ve neyi koruduğunu görmek için bir aşama seçin.",
    nodes: [
      { title: "Hedef", detail: "Kimliği doğrulanmış niyet", description: "Oturum açmış kullanıcının istediği sonucu; tenant/proje bağlamı, kabul kriterleri ve yetkili bağlam ile birlikte sınırlandırılmış işe dönüştürür. Hedef sonucu tarif eder; kendi kendine yetki vermez." },
      { title: "Politika", detail: "Yetki sınırı", description: "Yürütme kabul edilmeden önce kimlik, tenant izolasyonu, izinler, gizlilik/residency, DLP/secrets, araç kapsamı, risk, onay ve bütçe sınırlarını uygular. Yetki politikadadır; modelde değildir." },
      { title: "Yönlendirici", detail: "Yetenek seçimi", description: "Kabul edilmiş kapsam içinde uygun yetenek, model, araç veya sağlayıcıyı seçen tek yönetilen RoutingDecision üretir. Yönlendirme yürütmeyi optimize edebilir ancak izinleri genişletemez." },
      { title: "Üretim", detail: "Sınırlandırılmış yürütme", description: "Onaylı sınırlandırılmış DAG'ı uygun yerleşik factory ve yönetilen worker/araç/sağlayıcı yolu üzerinden yürütür. Factory'ler alan yürütme yüzeyleridir; paralel kontrol düzlemleri değildir." },
      { title: "Doğrulama", detail: "Kabul kontrolleri", description: "Bir çıktının ilerleyebilmesi için deterministik kontrolleri, güvenlik kapılarını ve açık kabul kriterlerini çalıştırır. Yalnızca üretilmiş olması bir çıktıyı bitmiş ürün yapmaz." },
      { title: "Kanıt", detail: "İncelenebilir kanıt", description: "Sonucun model iddialarına güvenmeden incelenebilmesi, denetlenebilmesi, kurtarılabilmesi ve açıklanabilmesi için doğrulama sonuçlarını, önemli olayları, provenance ve yürütme soyunu korur." },
      { title: "Sonuç", detail: "Kabul edilmiş çıktı", description: "Yalnız gerekli kabul kapıları geçildikten sonra bitmiş ürünü temsil eder. Teslim veya dış yan etkiler yetkili kapsam içinde gerçekleşir; iş akışının izin verdiği yerde checkpoint/resume ve bounded repair kullanılabilir." },
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
    <div ref={stageRef} className="spatial-stage" aria-label={c.aria} style={{ transform: "perspective(900px) rotateX(0deg) rotateY(0deg)" }} onPointerMove={event => { const rect = event.currentTarget.getBoundingClientRect(); tiltRef.current = { x: ((event.clientX - rect.left) / rect.width - 0.5) * 4, y: -((event.clientY - rect.top) / rect.height - 0.5) * 3 }; applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current); }} onPointerLeave={() => { tiltRef.current = { x: 0, y: 0 }; applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current); }}>
      {c.nodes.map((node, index) => <button type="button" className={`spatial-node spatial-node-${index + 1}${active === index ? " is-active" : ""}`} key={node.title} aria-pressed={active === index} aria-controls="spatial-map-detail" onClick={() => setActive(index)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{node.title}</strong><small>{node.detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</button>)}
    </div>
    <section id="spatial-map-detail" className="spatial-map-detail" aria-live="polite"><div><span className="micro-label">{String(active + 1).padStart(2, "0")} · {selected.title}</span><h3>{selected.detail}</h3><p>{selected.description}</p></div></section>
  </div>;
}
