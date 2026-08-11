import type { Metadata } from "next";
import Link from "next/link";

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
  ["06", "Verify independently", "Material work is not accepted solely because its author or executing agent reports success. Required independent verification remains risk-driven."],
  ["07", "Release preparation", "Version artifacts, capture build/test/security evidence, prepare rollback or recovery semantics, and keep environment progression explicit."],
  ["08", "Deliver & reconcile", "Deliver source/build/deployment preparation with traceable evidence; failures follow bounded diagnose, repair, retest, retry, or rollback paths."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Software Factory</div><h1>Software engineering with explicit boundaries and acceptance gates.</h1><p className="lead">Software Factory is the ILAIOS capability direction for converting software goals into governed engineering work rather than treating code generation as an unrestricted one-shot request.</p></section>
  <section className="section"><div className="shell"><p className="muted">ILAIOS tracks capability maturity separately from release state. This page describes the canonical product workflow and does not claim every Software Factory function is generally available today.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Governed delivery</div><h2>Generation, verification, and release authority remain separate where risk requires it.</h2></div><div className="actions"><Link className="button" href="/platform/validation">Validation model</Link><Link className="button secondary" href="/how-it-works">How ILAIOS works</Link></div></div></section>
</>; }
