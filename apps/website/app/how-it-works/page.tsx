import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How ILAIOS Works",
  description: "See how ILAIOS turns one stated outcome into governed work through policy, bounded execution, independent validation, evidence, delivery, monitoring and recovery.",
  alternates: { canonical: "/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const simple = [
  ["01", "Describe the finished outcome", "The user states what should be completed rather than selecting internal models, agents or providers."],
  ["02", "ILAIOS governs execution", "The platform resolves authority, plans bounded work and routes the appropriate deterministic or intelligent capabilities."],
  ["03", "Required checks decide acceptance", "Validation, evidence and approvals determine whether the result can advance."],
  ["04", "Receive accepted work", "A finished-product workflow returns a reviewable result; external side effects remain separately controlled."],
] as const;

const steps = [
  ["01", "Goal & trusted context", "A user or organization defines the desired outcome. Identity, tenant, project, and validated context establish the operating boundary."],
  ["02", "Policy & authorization", "Tool scopes, targets, risk, budget, and approval requirements are resolved before sensitive execution."],
  ["03", "Plan & orchestrate", "Work is decomposed into ordered, bounded jobs and routed to deterministic services or intelligent capabilities."],
  ["04", "Execute inside scope", "Agents, skills, workers, and tools act only within granted authority. Clients remain projections of backend state."],
  ["05", "Validate independently", "Schemas, tests, policy checks, technical probes, and acceptance criteria decide whether an outcome may advance."],
  ["06", "Evidence & approval", "Relevant actions, validation results, provenance, and decisions are retained. Human approval is required where policy demands it."],
  ["07", "Deliver & monitor", "Accepted artifacts or operational outcomes move to delivery, deployment, or publishing preparation and remain observable."],
  ["08", "Recover & audit", "Retryable failures follow bounded recovery. Other failures stop or escalate with a reviewable evidence trail."],
] as const;

const verified = ["Functional checks", "Browser QA", "Security checks", "Accessibility", "Performance", "SEO", "Visual QA", "Exact artifact identity", "Evidence", "Deployment validation when requested"] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">How ILAIOS Works</div><h1>Simple at the surface. Governed underneath.</h1><p className="lead">The canonical experience moves from a stated outcome toward accepted work without making the user operate the internal model, provider, agent or tool stack.</p></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">User-facing flow</div><h2>Outcome → execution → validation → finished result.</h2></div><p className="muted">This is product direction, not a claim that every factory function is generally available today.</p></div><div className="journey-grid">{simple.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Governance path</div><h2>Reasoning and authority stay separate.</h2></div><p className="muted">Models and agents may propose or perform bounded work; policy, authorization, durable state, validation, evidence, approvals and recovery remain governed by the platform.</p></div><div className="grid two-up">{steps.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">What verified means</div><h2>“Verified finished product” is an acceptance model, not a slogan.</h2></div><div><p className="lead small">The exact checks depend on the work domain. For a website, verification can include the following evidence families before acceptance.</p><div className="verification-list">{verified.map((item,i)=><div key={item}><span>{String(i+1).padStart(2,"0")}</span><strong>{item}</strong></div>)}</div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Production systems, not prompt theatre</div><h2>Execution is accepted only when the required controls and evidence pass.</h2><p className="muted">This operating model reduces silent or uncontrolled failure; it does not claim that software, models, providers, or infrastructure can never fail.</p></div><div className="actions"><Link className="button" href="/core">Explore ILAIOS Core</Link><Link className="button secondary" href="/architecture">Architecture</Link></div></div></section>
  </>;
}
