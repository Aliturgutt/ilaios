import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How ILAIOS Works",
  description: "See the public ILAIOS flow from describing an outcome to governed execution, verification and delivery.",
  alternates: { canonical: "/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const steps = [
  ["01", "Describe what you want finished", "Start with the outcome, references and constraints. You do not need to choose the internal model, agent or provider stack."],
  ["02", "ILAIOS organizes the work", "The system turns the request into bounded work and applies the permissions, policy and approvals required for that work."],
  ["03", "The work is produced", "The applicable capabilities execute the admitted work across web, software, media, research or a combination of them."],
  ["04", "ILAIOS verifies and delivers", "Required checks decide whether the result is accepted. If it passes, the finished result and its evidence are delivered; unresolved work does not become success by narrative."],
] as const;

const verified = [
  ["Works", "The required function or outcome is actually present."],
  ["Fits", "The result is checked against the stated acceptance criteria."],
  ["Safe", "Applicable policy, security and permission checks remain satisfied."],
  ["Traceable", "The accepted result retains the evidence needed to review what was delivered."],
] as const;

export default function Page() {
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">How ILAIOS Works</div><h1>Say what you need. ILAIOS manages the work to a verified result.</h1><p className="lead">The public experience is intentionally simple: describe the finished outcome, let ILAIOS govern and execute the work, then receive the result only after the required checks pass.</p><div className="actions"><Link className="button" href="/use-ilaios">Use ILAIOS</Link></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Four steps</div><h2>From one outcome to finished work.</h2></div><p>No provider selection, worker IDs or internal routing decisions are required from the user.</p></div><div className="journey-grid">{steps.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Product flow</div><h2>Goal → governed work → production → verification → delivery.</h2></div><p>This is the user-facing product path. Internal provider and execution details remain behind the product boundary.</p></div><div className="runtime-line">{steps.map(([n,t]) => <div key={n}><span>{n}</span><strong>{t}</strong></div>)}</div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">What verified means</div><h2>Verification answers a practical question: is this result ready to accept?</h2></div><p>The exact checks depend on the work being produced. Required acceptance checks cannot be skipped just to call the work finished.</p></div><div className="journey-grid">{verified.map(([title,text],i)=><article className="journey-card" key={title}><span>{String(i+1).padStart(2,"0")}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Need the technical model?</div><h2>The public flow stays simple; the architecture remains inspectable.</h2><p className="muted">Architecture, Core and Security explain the control and evidence model without forcing those internal details into the main product journey.</p></div><div className="actions"><Link className="button secondary" href="/architecture">Architecture</Link><Link className="button secondary" href="/core">Core</Link></div></div></section>
  </>;
}
