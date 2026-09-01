import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Software Factory",
  description: "How ILAIOS Software Factory structures software delivery as governed engineering jobs with bounded implementation, tests, review, security gates, release evidence, and recovery.",
  alternates: { canonical: "/factories/software", languages: { en: "/factories/software", tr: "/tr/factories/software", "x-default": "/factories/software" } },
};

const stages = [
  ["01", "Specify", "Define the requested outcome, repository or system boundary, constraints, acceptance criteria, risk, and required evidence."],
  ["02", "Plan", "Decompose work into bounded engineering jobs with dependencies, ownership, permissions, and a validation plan."],
  ["03", "Inspect before changing", "Use source, symbol, dependency, configuration, and runtime context where available instead of making blind edits."],
  ["04", "Implement inside scope", "Engineering capabilities modify only authorized files and systems; architecture and security boundaries remain authoritative."],
  ["05", "Test & review", "Run applicable deterministic tests, lint/type/static checks, code review, and security checks before acceptance."],
  ["06", "Verify independently", "Material work is not accepted solely because its author or executing process reports success. Required independent verification remains risk-driven."],
  ["07", "Release preparation", "Version artifacts, capture build/test/security evidence, prepare rollback or recovery semantics, and keep environment progression explicit."],
  ["08", "Deliver & reconcile", "Deliver source/build/deployment preparation with traceable evidence; failures follow bounded diagnose, repair, retest, retry, or rollback paths."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Software Factory</div><h1>Software engineering with explicit boundaries and acceptance gates.</h1><p className="lead">Software Factory converts software goals into governed engineering work rather than treating code generation as an unrestricted one-shot request.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Preview</span><p>The bounded local Windows finished-product scope is repository-verified. Arbitrary external-repository effects, software breadth and commercial release are not implied by that evidence.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Software Factory at a glance</div><h2>Turn requirements into tested, reviewable software changes.</h2></div><p>The target visual keeps requirements, implementation, tests, review, bounded repair and handoff visible without treating a code diff as completion.</p></div><ThemedDiagram light="/visuals/software-light.avif" dark="/visuals/software-dark.avif" alt="ILAIOS Software Factory diagram showing requirement and context, scope and plan, implementation, tests, review, bounded repair and tested change" caption="Target workflow: requirement + context → scope & plan → implement → test → review → bounded repair → tested change." priority /></div></section>

  <section className="section"><div className="shell"><p className="muted">ILAIOS tracks capability maturity separately from release state. Repository verification for a bounded scope does not claim every Software Factory function or external effect is generally available today.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Governed delivery</div><h2>Implementation, verification, merge and release authority remain separate where risk requires it.</h2><p className="muted">A tested change is not automatically merged, deployed or production-verified. Those transitions require their own evidence.</p></div><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/platform/validation">Validation model</Link></div></div></section>
</>; }
