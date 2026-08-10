import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ILAIOS",
  description: "ILAIOS builds governed infrastructure for intelligent automation and autonomous operations.",
  alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/" } },
};

const pillars = [
  ["Governed", "Critical actions are constrained by explicit policies, permissions, approvals, and observable control paths."],
  ["Verifiable", "Execution is designed around evidence, validation, auditability, and deterministic behavior where possible."],
  ["Composable", "Clients, services, agents, and workflows are separated by durable contracts instead of fragile presentation-layer coupling."],
] as const;

const flow = [
  ["01", "Intent", "A goal enters through a client or approved interface."],
  ["02", "Policy", "Authority, permissions, and execution constraints are evaluated."],
  ["03", "Execution", "Deterministic tools and bounded intelligent capabilities perform the work."],
  ["04", "Verification", "Tests, validators, and evidence determine whether the result is acceptable."],
  ["05", "Delivery", "Validated outputs are surfaced to the user with an observable trail."],
] as const;

export default function Home() {
  return <>
    <section className="shell hero"><div className="hero-copy"><div className="eyebrow">Intelligent systems. Governed execution.</div><h1>Build autonomy you can control.</h1><p className="lead">ILAIOS is developing infrastructure for intelligent automation with explicit control boundaries, verifiable execution, and security-first operations.</p><div className="actions"><Link className="button" href="/platform">Explore the platform</Link><Link className="button secondary" href="/about">Why ILAIOS</Link></div><div className="hero-meta" aria-label="Development status"><span className="status-dot" /> Active development <span className="meta-separator">•</span> Architecture-led <span className="meta-separator">•</span> Evidence-first</div></div><div className="hero-visual" aria-hidden="true"><Image src="/brand/website-hero.jpg" alt="" width={1920} height={1080} priority sizes="(max-width: 900px) calc(100vw - 40px), 48vw" quality={82} /></div></section>
    <section className="section"><div className="shell"><div className="eyebrow">Design principles</div><h2>Autonomy without surrendering control.</h2><div className="grid">{pillars.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Control architecture</div><h2>One governed path from intent to evidence.</h2></div><p className="lead small">The public interface is not the authority. ILAIOS is designed around a control plane that evaluates policy, coordinates execution, verifies outcomes, and preserves evidence.</p></div><div className="control-stack"><div className="stack-layer client-layer"><span>CLIENT LAYER</span><strong>Desktop · Mobile · Web</strong><small>Goals, approvals, observability and delivery</small></div><div className="stack-connector">↓ governed requests / observable results ↑</div><div className="stack-layer authority-layer"><span>AUTHORITATIVE CONTROL PLANE</span><strong>Policy · Orchestration · Permissions · Validation</strong><small>Decision authority remains outside presentation clients</small></div><div className="stack-connector">↓ bounded execution / evidence ↑</div><div className="stack-layer execution-layer"><span>EXECUTION LAYER</span><strong>Tools · Services · Agents · Workflows</strong><small>Deterministic paths first; intelligent capabilities where appropriate</small></div></div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Execution lifecycle</div><h2>Work should be inspectable, not mysterious.</h2></div><p className="lead small">The target operating model makes meaningful transitions explicit so users can understand what is happening and why.</p></div><div className="flow-grid">{flow.map(([number,title,text]) => <article className="flow-card" key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section evidence-section"><div className="shell evidence-grid"><div><div className="eyebrow">Evidence & security</div><h2>Trust should come from controls and proof.</h2><p className="lead small">ILAIOS is being engineered so sensitive actions can be bounded by permissions, approval gates, validation, and auditable evidence instead of relying on an agent simply claiming success.</p><div className="actions"><Link className="text-link" href="/security">Read the security direction →</Link></div></div><div className="evidence-panel" aria-label="Illustrative verification chain"><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Policy check</strong><small>Authority evaluated before execution</small></div></div><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Validation gate</strong><small>Outcome checked against explicit criteria</small></div></div><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Evidence trail</strong><small>Meaningful execution events remain observable</small></div></div></div></div></section>
    <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Development status</div><h2>Building in public, without overstating what is ready.</h2></div><div><p className="muted">This site distinguishes engineering direction from released capability. Planned features are not presented as commercially available until they are actually validated and released.</p></div></div></section>
  </>;
}
