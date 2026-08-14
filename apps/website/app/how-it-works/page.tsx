import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../CanonicalSystemDetail";

export const metadata: Metadata = {
  title: "How ILAIOS Works",
  description: "See how ILAIOS turns one stated outcome into governed work through identity, policy, bounded execution, one routing decision, independent validation, evidence and recovery.",
  alternates: { canonical: "/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const simple = [
  ["01", "Describe the finished outcome", "The user states what should be completed rather than selecting internal models, agents or providers."],
  ["02", "ILAIOS establishes the execution contract", "Identity, tenant/project context, requirements, acceptance criteria and authorized context define the bounded goal."],
  ["03", "Governed work executes", "Admission, approval when required, ONE RoutingDecision and bounded workers move admitted tasks through the workflow."],
  ["04", "Independent checks decide finality", "Validation, evidence, bounded repair and final evaluation determine whether the result is accepted or safely stopped."],
] as const;

const verified = ["Functional checks", "Browser QA", "Security checks", "Accessibility", "Performance", "SEO", "Visual QA", "Exact artifact identity", "Evidence / provenance", "Deployment validation when requested"] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">How ILAIOS Works</div><h1>Simple at the surface. Governed underneath.</h1><p className="lead">The canonical experience moves from sign-in and one natural-language goal toward accepted work without making the user operate the internal model, provider, agent or tool stack.</p></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">User-facing flow</div><h2>Outcome → governed execution → independent acceptance → finished result.</h2></div><p className="muted">This is canonical product direction. Current availability is proven separately by implementation, tests, CI, runtime and deployment evidence.</p></div><div className="journey-grid">{simple.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><CanonicalSystemDetail locale="en" variant="journey" /></div></section>
    <section className="section"><div className="shell"><CanonicalSystemDetail locale="en" variant="runtime" /></div></section>
    <section className="section surface-section"><div className="shell"><CanonicalSystemDetail locale="en" variant="recovery" /></div></section>
    <section className="section"><div className="shell"><CanonicalSystemDetail locale="en" variant="cost" /></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">What verified means</div><h2>“Verified finished product” is an acceptance model, not a slogan.</h2></div><div><p className="lead small">Final evaluation applies the required domain criteria to the complete artifact or action outcome. Where feasible, the producer is not the sole verifier of its own result.</p><div className="verification-list">{verified.map((item,i)=><div key={item}><span>{String(i+1).padStart(2,"0")}</span><strong>{item}</strong></div>)}</div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Production systems, not prompt theatre</div><h2>Execution is accepted only when the required controls and evidence pass.</h2><p className="muted">A policy/security denial cannot be repaired by bypassing policy. Repair is bounded by attempts, cost and elapsed time; unresolved work stops or escalates.</p></div><div className="actions"><Link className="button" href="/core">Explore ILAIOS Core</Link><Link className="button secondary" href="/architecture">Architecture</Link></div></div></section>
  </>;
}
