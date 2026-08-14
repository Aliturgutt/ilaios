"use client";

import { useEffect, useRef, useState } from "react";

type Locale = "en" | "tr";

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

export default function SpatialArchitecture({ locale, compact = false }: { locale: Locale; compact?: boolean }) {
  const c = copy[locale];
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [scrollDepth, setScrollDepth] = useState(0);

  useEffect(() => {
    const update = () => {
      if (!wrapperRef.current || window.innerWidth < 760 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setScrollDepth(0);
        return;
      }
      const rect = wrapperRef.current.getBoundingClientRect();
      const viewportCenter = window.innerHeight / 2;
      const elementCenter = rect.top + rect.height / 2;
      const normalized = Math.max(-1, Math.min(1, (viewportCenter - elementCenter) / Math.max(window.innerHeight, 1)));
      setScrollDepth(normalized * 1.6);
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
      className="spatial-stage"
      role="img"
      aria-label={c.aria}
      style={{ transform: `perspective(900px) rotateX(${tilt.y + scrollDepth}deg) rotateY(${tilt.x}deg)` }}
      onPointerMove={event => {
        const rect = event.currentTarget.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width - 0.5) * 4;
        const y = -((event.clientY - rect.top) / rect.height - 0.5) * 3;
        setTilt({ x, y });
      }}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      {c.nodes.map(([title, detail], index) => <div className={`spatial-node spatial-node-${index + 1}`} key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small>{index < c.nodes.length - 1 && <i aria-hidden="true" />}</div>)}
    </div>
  </div>;
}
