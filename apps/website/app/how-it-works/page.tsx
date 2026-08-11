import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How ILAIOS Works",
  description: "See how ILAIOS turns goals into governed work through identity, policy, orchestration, bounded execution, validation, evidence, approval, delivery, monitoring, and recovery.",
  alternates: { canonical: "/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

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

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">How ILAIOS Works</div><h1>From a goal to a controlled, reviewable outcome.</h1><p className="lead">ILAIOS separates reasoning from authority. Models and agents may propose or perform bounded work, while policy, authorization, durable state, validation, evidence, approvals, and recovery remain governed by the platform.</p></section>
    <section className="section"><div className="shell"><div className="grid two-up">{steps.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Production systems, not prompt theatre</div><h2>Execution is accepted only when the required controls and evidence pass.</h2><p className="muted">This operating model reduces silent or uncontrolled failure; it does not claim that software, models, providers, or infrastructure can never fail.</p></div><div className="actions"><Link className="button" href="/core">Explore ILAIOS Core</Link><Link className="button secondary" href="/architecture">Architecture</Link></div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Specialized factories</div><h2>Repeatable production workflows share the same governance model.</h2></div></div><div className="grid three-up"><Link className="card card-link" href="/factories/web"><h3>Web Factory</h3><p>Requirements → information architecture → implementation → QA → deployment readiness.</p></Link><Link className="card card-link" href="/factories/software"><h3>Software Factory</h3><p>Plan → bounded engineering → tests → review → release evidence.</p></Link><Link className="card card-link" href="/factories/video"><h3>Video / Media Factory</h3><p>Research → script → scenes → media → render → validation → publishing preparation.</p></Link></div></div></section>
  </>;
}
