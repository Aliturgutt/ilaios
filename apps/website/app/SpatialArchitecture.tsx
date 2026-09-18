"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Importers/callers: Imported by ArchitecturePage.tsx
 * Affected API: React component using useEffect, useRef, useState for 3D spatial interaction
 * Data schemas: Props (locale: "en" | "tr", compact?: boolean), Node interface with title, detail, description
 * User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README file. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.
 */

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
      { title: "Kanıt", detail: "İncelenebilir kanıt", description: "Sonucun model iddialarına güvemen incelenebilmesi, denetlenebilmesi, kurtarılabilmesi ve açıklanabilmesi için doğrulama sonuçlarını, önemli olayları, provenance ve yürütme soyunu korur." },
      { title: "Sonuç", detail: "Kabul edilmiş çıktı", description: "Yalnız gerekli kabul kapıları geçildikten sonra bitmiş ürünü temsil eder. Teslim veya dış yan etkiler yetkili kapsam içinde gerçekleşir; iş akışının izin verdiği yerde checkpoint/resume ve bounded repair kullanılabilir." },
    ],
  },
};

function applyStageTransform(stage: HTMLDivElement | null, tilt: Tilt) {
  if (!stage) return;
  stage.style.transform = `perspective(900px) rotateX(${tilt.y}deg) rotateY(${tilt.x}deg)`;
}

export default function SpatialArchitecture({ locale, compact = false }: { locale: Locale; compact?: boolean }) {
  const c = copy[locale];
  const [active, setActive] = useState(0);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const baseTiltRef = useRef<Tilt>({ x: 0, y: 0 });
  const pointerOffsetRef = useRef<Tilt>({ x: 0, y: 0 });
  const frameRef = useRef<number | null>(null);
  const reducedMotionRef = useRef<boolean>(false);

  useEffect(() => {
    const updateReducedMotion = () => {
      reducedMotionRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    };
    updateReducedMotion();
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", updateReducedMotion);
    return () => mq.removeEventListener("change", updateReducedMotion);
  }, []);

  useEffect(() => {
    const frame = frameRef.current;

    const update = () => {
      const wrapper = wrapperRef.current;
      if (!wrapper || window.innerWidth < 760 || reducedMotionRef.current) {
        // Reset when not active
        baseTiltRef.current = { x: 0, y: 0 };
        pointerOffsetRef.current = { x: 0, y: 0 };
        if (stageRef.current) {
          applyStageTransform(stageRef.current, {
            x: baseTiltRef.current.x + pointerOffsetRef.current.x,
            y: baseTiltRef.current.y + pointerOffsetRef.current.y
          });
        }
        return;
      }

      const rect = wrapper.getBoundingClientRect();
      const sectionTop = rect.top + window.scrollY;
      const sectionHeight = rect.height;
      const viewportHeight = window.innerHeight;

      // Scroll progress: 0 at top, 1 at bottom
      let progress = (window.scrollY + viewportHeight / 2 - sectionTop) / (sectionHeight - viewportHeight / 2);
      progress = Math.max(0, Math.min(1, progress));

      // Map progress to node index
      const targetIndex = Math.round(progress * (c.nodes.length - 1));
      if (targetIndex !== active) {
        setActive(targetIndex);
      }

      // Base tilt from progress: subtle rotation as user scrolls through
      // Tilt Y: from -10deg to +10deg, Tilt X: from -5deg to +5deg
      baseTiltRef.current = {
        x: (progress - 0.5) * 10, // -5 to +5
        y: (progress - 0.5) * 20  // -10 to +10
      };

      // Apply combined tilt
      if (stageRef.current) {
        applyStageTransform(stageRef.current, {
          x: baseTiltRef.current.x + pointerOffsetRef.current.x,
          y: baseTiltRef.current.y + pointerOffsetRef.current.y
        });
      }
    };

    const onPointerMove = (event: PointerEvent) => {
      if (reducedMotionRef.current || !wrapperRef.current || window.innerWidth < 760) return;
      const rect = stageRef.current?.getBoundingClientRect();
      if (!rect) return;
      // Pointer offset: subtle additional tilt based on cursor position within stage
      const pointerX = (event.clientX - rect.left) / rect.width - 0.5; // -0.5 to +0.5
      const pointerY = (event.clientY - rect.top) / rect.height - 0.5; // -0.5 to +0.5
      pointerOffsetRef.current = {
        x: pointerX * 10, // -5 to +5 degrees
        y: pointerY * 20  // -10 to +10 degrees
      };
      // Apply combined tilt
      if (stageRef.current) {
        applyStageTransform(stageRef.current, {
          x: baseTiltRef.current.x + pointerOffsetRef.current.x,
          y: baseTiltRef.current.y + pointerOffsetRef.current.y
        });
      }
    };

    const onPointerLeave = () => {
      pointerOffsetRef.current = { x: 0, y: 0 };
      if (stageRef.current) {
        applyStageTransform(stageRef.current, {
          x: baseTiltRef.current.x + pointerOffsetRef.current.x,
          y: baseTiltRef.current.y + pointerOffsetRef.current.y
        });
      }
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerleave", onPointerLeave);

    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [active, c.nodes.length]);

  const selected = c.nodes[active];
  return <div ref={wrapperRef} className={`spatial-map ${compact ? "is-compact" : ""}`} data-visual-role="architecture-spatial-map">
    <div className="spatial-map-head"><span className="micro-label">{c.label}</span><small>{c.hint}</small></div>
    <div ref={stageRef} className="spatial-stage dark-surface" aria-label={c.aria} style={{ transform: "perspective(900px) rotateX(0deg) rotateY(0deg)" }} >
      {c.nodes.map((node, index) => <button type="button" className={`spatial-node spatial-node-${index + 1}${active === index ? " is-active" : ""}`} key={node.title} aria-pressed={active === index} aria-controls="spatial-map-detail" onClick={() => setActive(index)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{node.title}</strong><small>{node.detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</button>)}
    </div>
    <section id="spatial-map-detail" className="spatial-map-detail" aria-live="polite"><div><span className="micro-label">{String(active + 1).padStart(2, "0")} · {selected.title}</span><h3>{selected.detail}</h3><p>{selected.description}</p></div></section>
  </div>;
}
