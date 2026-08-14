"use client";

import { useEffect, useRef } from "react";

type Locale = "en" | "tr";
type Tilt = { x: number; y: number };

const copy = {
  en: {
    label: "Governed execution map",
    aria: "ILAIOS governed execution architecture from goal through policy, routing, factory execution, validation, evidence and result",
    nodes: [
      ["Goal", "Authenticated intent"],
      ["Policy", "Authority boundary"],
      ["Router", "Capability selection"],
      ["Factory", "Bounded execution"],
      ["Validation", "Acceptance checks"],
      ["Evidence", "Reviewable proof"],
      ["Result", "Accepted outcome"],
    ],
  },
  tr: {
    label: "Yönetilen yürütme haritası",
    aria: "Hedeften politika, yönlendirme, üretim, doğrulama, kanıt ve kabul edilmiş sonuca uzanan ILAIOS yönetilen yürütme mimarisi",
    nodes: [
      ["Hedef", "Kimliği doğrulanmış niyet"],
      ["Politika", "Yetki sınırı"],
      ["Yönlendirici", "Yetenek seçimi"],
      ["Üretim", "Sınırlandırılmış yürütme"],
      ["Doğrulama", "Kabul kontrolleri"],
      ["Kanıt", "İncelenebilir kanıt"],
      ["Sonuç", "Kabul edilmiş çıktı"],
    ],
  },
} as const;

function applyStageTransform(stage: HTMLDivElement | null, tilt: Tilt, scrollDepth: number) {
  if (!stage) return;
  stage.style.transform = `perspective(900px) rotateX(${tilt.y + scrollDepth}deg) rotateY(${tilt.x}deg)`;
}

export default function SpatialArchitecture({ locale, compact = false }: { locale: Locale; compact?: boolean }) {
  const c = copy[locale];
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
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return <div ref={wrapperRef} className={`spatial-map ${compact ? "is-compact" : ""}`} data-visual-role="architecture-spatial-map">
    <div className="spatial-map-head"><span className="micro-label">{c.label}</span><small>{locale === "tr" ? "Masaüstünde imleç ve kaydırma katman ilişkisini gösterir. Mobilde düzleştirilir." : "Pointer and scroll expose layer relationships on desktop. The map flattens on mobile."}</small></div>
    <div
      ref={stageRef}
      className="spatial-stage"
      role="img"
      aria-label={c.aria}
      style={{ transform: "perspective(900px) rotateX(0deg) rotateY(0deg)" }}
      onPointerMove={event => {
        const rect = event.currentTarget.getBoundingClientRect();
        tiltRef.current = {
          x: ((event.clientX - rect.left) / rect.width - 0.5) * 4,
          y: -((event.clientY - rect.top) / rect.height - 0.5) * 3,
        };
        applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current);
      }}
      onPointerLeave={() => {
        tiltRef.current = { x: 0, y: 0 };
        applyStageTransform(stageRef.current, tiltRef.current, scrollDepthRef.current);
      }}
    >
      {c.nodes.map(([title, detail], index) => <div className={`spatial-node spatial-node-${index + 1}`} key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</div>)}
    </div>
  </div>;
}
