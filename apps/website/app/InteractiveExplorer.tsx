"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Interactive system tour",
    title: "Explore the operating model without leaving the page.",
    intro: "Select a stage to see what changes, who remains authoritative, and where to continue for detail.",
    stages: [
      { label: "Control", title: "Policy decides before execution begins.", text: "Identity, permissions, tenant context, approval requirements, and execution conditions stay in the authoritative control plane.", points: ["Explicit authority boundaries", "Policy before tool access", "Client requests are not system truth"], href: "/platform/control-plane", cta: "Explore control plane" },
      { label: "Execute", title: "Use deterministic paths first.", text: "Reliable rules, validators, and bounded tools are preferred when they can solve the task; intelligent capabilities operate inside defined contracts.", points: ["Bounded tools", "Deterministic checks", "Escalation when uncertainty matters"], href: "/platform/execution", cta: "Explore execution" },
      { label: "Verify", title: "Results are checked before they are trusted.", text: "Validation gates and approval requirements determine whether an outcome can advance instead of treating a model response as proof of success.", points: ["Validation gates", "Approval boundaries", "Fail-closed behavior for sensitive work"], href: "/security/approvals", cta: "Explore approvals" },
      { label: "Observe", title: "Evidence makes important work reviewable.", text: "Meaningful execution events, validation outcomes, and audit context are designed to remain inspectable for review and recovery.", points: ["Evidence records", "Audit context", "Operational visibility"], href: "/platform/evidence", cta: "Explore evidence" },
    ],
  },
  tr: {
    eyebrow: "Etkileşimli sistem turu",
    title: "Sayfadan ayrılmadan işletim modelini inceleyin.",
    intro: "Bir aşama seçerek neyin değiştiğini, otoritenin nerede kaldığını ve ayrıntı için nereye ilerleyeceğinizi görün.",
    stages: [
      { label: "Kontrol", title: "Yürütme başlamadan önce politika karar verir.", text: "Kimlik, izinler, tenant bağlamı, onay gereksinimleri ve yürütme koşulları yetkili kontrol katmanında kalır.", points: ["Açık yetki sınırları", "Araç erişiminden önce politika", "İstemci isteği sistem gerçeği değildir"], href: "/tr/platform/control-plane", cta: "Kontrol katmanını incele" },
      { label: "Yürüt", title: "Önce deterministik yolları kullanın.", text: "Görevi güvenilir biçimde çözebildiğinde kurallar, doğrulayıcılar ve sınırlandırılmış araçlar tercih edilir; akıllı yetenekler tanımlı sözleşmeler içinde çalışır.", points: ["Sınırlandırılmış araçlar", "Deterministik kontroller", "Belirsizlik önemliyse eskalasyon"], href: "/tr/platform/execution", cta: "Yürütmeyi incele" },
      { label: "Doğrula", title: "Sonuçlar güvenilmeden önce kontrol edilir.", text: "Doğrulama kapıları ve onay gereksinimleri sonucun ilerleyip ilerleyemeyeceğini belirler; model yanıtı tek başına başarı kanıtı sayılmaz.", points: ["Doğrulama kapıları", "Onay sınırları", "Hassas işlerde fail-closed davranış"], href: "/tr/security/approvals", cta: "Onayları incele" },
      { label: "Gözlemle", title: "Kanıt önemli işi incelenebilir kılar.", text: "Anlamlı yürütme olayları, doğrulama sonuçları ve denetim bağlamı inceleme ve kurtarma için görünür kalacak şekilde tasarlanır.", points: ["Kanıt kayıtları", "Denetim bağlamı", "Operasyonel görünürlük"], href: "/tr/platform/evidence", cta: "Kanıtı incele" },
    ],
  },
} as const;

export default function InteractiveExplorer({ locale }: { locale: Locale }) {
  const [active, setActive] = useState(0);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const data = copy[locale];
  const stage = data.stages[active];
  const move = (next: number) => {
    const index = (next + data.stages.length) % data.stages.length;
    setActive(index);
    tabRefs.current[index]?.focus();
  };
  return <section className="section interactive-section" id="how-it-works">
    <div className="shell interactive-shell">
      <div className="section-heading compact-heading"><div><div className="eyebrow">{data.eyebrow}</div><h2>{data.title}</h2></div><p className="lead small">{data.intro}</p></div>
      <div className="interactive-explorer">
        <div className="explorer-tabs" role="tablist" aria-label={locale === "tr" ? "Sistem aşamaları" : "System stages"}>
          {data.stages.map((item, index) => <button key={item.label} ref={element => { tabRefs.current[index] = element; }} id={`explorer-tab-${locale}-${index}`} type="button" role="tab" aria-selected={active === index} aria-controls={`explorer-panel-${locale}`} tabIndex={active === index ? 0 : -1} className={active === index ? "is-active" : ""} onClick={() => setActive(index)} onKeyDown={event => { if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); move(active + 1); } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); move(active - 1); } else if (event.key === "Home") { event.preventDefault(); move(0); } else if (event.key === "End") { event.preventDefault(); move(data.stages.length - 1); } }}><span>0{index + 1}</span>{item.label}</button>)}
        </div>
        <div id={`explorer-panel-${locale}`} className="explorer-panel" role="tabpanel" aria-labelledby={`explorer-tab-${locale}-${active}`} tabIndex={0}>
          <div><span className="panel-kicker">{stage.label}</span><h3>{stage.title}</h3><p>{stage.text}</p></div>
          <ul>{stage.points.map(point => <li key={point}>{point}</li>)}</ul>
          <Link className="button secondary" href={stage.href}>{stage.cta} →</Link>
        </div>
      </div>
    </div>
  </section>;
}
