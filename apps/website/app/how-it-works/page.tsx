import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../CanonicalSystemDetail";
import ThemedDiagram from "../ThemedDiagram";

export const metadata: Metadata = {
  title: "How ILAIOS Works",
  description: "See how ILAIOS turns one stated outcome into governed work through identity, bounded planning, policy, capability resolution, execution, independent validation, evidence and recovery.",
  alternates: { canonical: "/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const simple = [
  ["01", "Describe the finished outcome", "The user states what should be completed rather than selecting internal models, agents or providers."],
  ["02", "ILAIOS establishes the execution contract", "Identity, tenant/project context, requirements, acceptance criteria and authorized context define the bounded goal."],
  ["03", "Governed work executes", "Admission, approval when required, capability resolution and bounded execution move admitted tasks through the appropriate production path."],
  ["04", "Independent checks decide finality", "Validation, evidence, bounded repair and final evaluation determine whether the result is accepted or safely stopped."],
] as const;

const verified = ["Functional checks", "Browser QA", "Security checks", "Accessibility", "Performance", "SEO", "Visual QA", "Exact artifact identity", "Evidence / provenance", "Deployment validation when requested"] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">How ILAIOS Works</div><h1>Simple at the surface. Governed underneath.</h1><p className="lead">The canonical experience moves from sign-in and one natural-language goal toward accepted work without making the user operate the internal model, provider or tool stack.</p><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/factories">Explore factories</Link></div></section>

    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">User-facing flow</div><h2>Outcome → governed execution → independent acceptance → finished result.</h2></div><p className="muted">This is canonical product direction. Current availability is proven separately by implementation, tests, CI, runtime and deployment evidence.</p></div><div className="journey-grid">{simple.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>

    <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Public workflow</div><h2>One goal. Governed execution. Verified result.</h2></div><p>The public diagram shows what a user needs to understand while internal provider/model routing remains behind the product boundary.</p></div><ThemedDiagram light="/visuals/general-flow-light.avif" dark="/visuals/general-flow-dark.avif" alt="ILAIOS public workflow from sign in and goal through understanding, planning, resolution, governance, execution, verification and delivery" caption="Public product workflow. Internal credentials, provider fallbacks, worker IDs and implementation details are intentionally not exposed." priority /></div></section>

    <section className="section"><div className="shell"><CanonicalSystemDetail locale="en" variant="journey" /></div></section>

    <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Governance & approval</div><h2>Capability is not authority.</h2></div><p>A factory, skill or execution resource can act only inside the authority admitted by identity, tenant scope, policy, risk, budget and approval requirements.</p></div><ThemedDiagram light="/visuals/governance-light.avif" dark="/visuals/governance-dark.avif" alt="ILAIOS governance and approval diagram showing request, policy checks, approval or routing, scoped execution and reviewable evidence" caption="Public governance model: explicit scope, policy first, approval when required and reviewable execution." /></div></section>

    <section className="section"><div className="shell"><CanonicalSystemDetail locale="en" variant="runtime" /></div></section>
    <section className="section surface-section"><div className="shell"><CanonicalSystemDetail locale="en" variant="recovery" /></div></section>

    <section className="section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Verification, evidence & repair</div><h2>A result is accepted only after the required checks pass.</h2></div><p>Evidence is retained, repair remains bounded, and unresolved work stops or escalates instead of being promoted by narrative alone.</p></div><ThemedDiagram light="/visuals/verification-light.avif" dark="/visuals/verification-dark.avif" alt="ILAIOS verification, evidence and bounded repair diagram from result arrival through validation, evidence capture, repair and accept or stop" caption="Verification is a gate, not decoration: required criteria decide whether a produced result can be accepted." /></div></section>

    <section className="section"><div className="shell"><CanonicalSystemDetail locale="en" variant="cost" /></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">What verified means</div><h2>“Verified finished product” is an acceptance model, not a slogan.</h2></div><div><p className="lead small">Final evaluation applies the required domain criteria to the complete artifact or action outcome. Where feasible, the producer is not the sole verifier of its own result.</p><div className="verification-list">{verified.map((item,i)=><div key={item}><span>{String(i+1).padStart(2,"0")}</span><strong>{item}</strong></div>)}</div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Production systems, not prompt theatre</div><h2>Execution is accepted only when the required controls and evidence pass.</h2><p className="muted">A policy/security denial cannot be repaired by bypassing policy. Repair is bounded by attempts, cost and elapsed time; unresolved work stops or escalates.</p></div><div className="actions"><Link className="button" href="/core">Explore ILAIOS Core</Link><Link className="button secondary" href="/architecture">Architecture</Link></div></div></section>
  </>;
}
