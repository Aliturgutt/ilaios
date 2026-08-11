import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Solutions", description: "Explore ILAIOS solution patterns for governed intelligent automation across AI operations, engineering, security, business processes, and research.", alternates: { canonical: "/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["AI operations", "Coordinate model-assisted work behind explicit policy, approvals, validation, and evidence rather than treating model output as authority.", ["Bound model/tool permissions", "Require approval for sensitive side effects", "Preserve validation and evidence"]],
  ["Software engineering", "Structure engineering tasks as bounded jobs with tool permissions, deterministic checks, review gates, and traceable execution outcomes.", ["Separate planning from execution authority", "Run deterministic quality gates", "Retain reviewable execution context"]],
  ["Security operations", "Support controlled security workflows where sensitive actions remain permission-bound, reviewable, and auditable.", ["Scope tools and targets explicitly", "Escalate high-impact actions", "Record meaningful security events"]],
  ["Business process automation", "Combine deterministic workflow steps with intelligent capabilities while keeping business rules and authorization outside the model.", ["Encode business constraints outside prompts", "Use deterministic steps where possible", "Verify completion before delivery"]],
  ["Research & knowledge work", "Organize evidence-backed research and synthesis with source traceability, validation, and explicit escalation paths.", ["Keep source provenance visible", "Separate findings from decisions", "Escalate uncertainty instead of hiding it"]],
] as const;

const operatingModel = [
  ["1", "Define authority", "Identify who may request work, which tools may be used, and which side effects require approval."],
  ["2", "Bound execution", "Route the job through deterministic services or explicitly constrained intelligent capabilities."],
  ["3", "Validate outcome", "Check the result against acceptance criteria rather than relying on a narrative success claim."],
  ["4", "Preserve evidence", "Keep enough operational context to support review, recovery, and accountable delivery."],
] as const;

export default function Solutions(){return <>
  <section className="shell page-hero"><div className="eyebrow">Solutions</div><h1>Intelligent work, bounded by operational control.</h1><p className="lead">ILAIOS is designed for workflows where automation must remain useful without becoming unaccountable. The same governed execution model can support different operational domains while authority, validation, and evidence remain explicit.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Solution patterns</div><h2>Apply intelligence without moving authority into the model.</h2></div><p className="muted">These patterns describe the product and architecture direction of ILAIOS. They do not claim released customer deployments or generally available integrations.</p></div><div className="grid two-up">{solutions.map(([title,text,points])=><article className="card" key={title}><h3>{title}</h3><p>{text}</p><ul>{points.map(point=><li key={point}>{point}</li>)}</ul></article>)}</div></div></section>
  <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Operating model</div><h2>From request to accepted outcome.</h2></div><p className="muted">A solution is not only a prompt or agent. It is a governed path that connects authority, execution, validation, and evidence.</p></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Choosing a path</div><h2>Start from operational risk, not from model capability.</h2></div><div><p className="lead small">The right automation path depends on the authority required, the reversibility of side effects, the quality of deterministic checks, and the evidence needed after execution.</p><p className="muted">ILAIOS favors deterministic execution whenever it can satisfy the task, and introduces intelligent capabilities where they add value inside explicit boundaries.</p><div className="actions"><Link className="button secondary" href="/architecture">Architecture</Link><Link className="button secondary" href="/security">Security model</Link><Link className="text-link" href="/trust">Trust Center →</Link></div></div></div></section>
</>}
