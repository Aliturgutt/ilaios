import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Solutions", description: "Explore ILAIOS solution patterns for governed research, enterprise intelligence, business operations and digital production.", alternates: { canonical: "/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Product launch", "Coordinate research, market intelligence, strategy, budget/risk, web, software/app, media, growth and measurement under one governed execution model.", ["Resolve one business goal into bounded work", "Compose multiple factories without parallel authority", "Preserve validation and evidence across the outcome"]],
  ["Digital business operations", "Coordinate tasks, processes, execution monitoring, exceptions and approval-gated business actions without turning business functions into autonomous departments.", ["Keep business rules outside model authority", "Escalate sensitive or irreversible actions", "Retain operational evidence"]],
  ["Research & intelligence", "Combine source-grounded research, competitive intelligence, KPI/performance analysis and evidence-backed recommendations.", ["Keep provenance visible", "Separate analysis from decision authority", "Escalate uncertainty instead of hiding it"]],
  ["Software delivery", "Structure web, software and application work as bounded production paths with deterministic checks, review gates and traceable release evidence.", ["Separate planning from execution authority", "Run deterministic quality gates", "Require release/deployment authority separately"]],
  ["Content & growth", "Compose market intelligence, campaign planning, web/video/document production and measurement-oriented growth workflows.", ["Keep publishing separately authorized", "Use evidence-backed measurement", "Treat current integrations as maturity-gated"]],
  ["Governed enterprise automation", "Combine deterministic workflow steps with intelligent capabilities while policy, approvals, authorization, validation and evidence remain outside the model.", ["Encode constraints outside prompts", "Prefer deterministic execution where sufficient", "Verify completion before delivery"]],
] as const;

const operatingModel = [
  ["1", "Business goal", "Capture the authenticated outcome and acceptance criteria."],
  ["2", "Resolve work", "Use research, intelligence, operations, shared capabilities and factories as needed."],
  ["3", "Govern execution", "Policy, approvals, tenant context, routing and bounded tools constrain every admitted action."],
  ["4", "Validate outcome", "Check the result against acceptance criteria rather than narrative success."],
  ["5", "Preserve evidence", "Keep enough context for review, recovery and accountable delivery."],
] as const;

const launchFlow = ["Business Goal", "Research", "Market / Competitive Intelligence", "Strategy", "Budget / Risk", "Web", "Software / App", "Video / Content", "Growth", "Commerce", "Measurement", "Evidence"] as const;

export default function Solutions(){return <>
  <section className="shell page-hero"><div className="eyebrow">Solutions</div><h1>Business goals become governed, cross-functional outcomes.</h1><p className="lead">ILAIOS is designed to coordinate research, intelligence, operations and digital production under one execution authority. A solution is not a department or a prompt; it is a governed path from business intent to reviewable evidence.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Solution patterns</div><h2>Start from the outcome, then compose the work that is actually needed.</h2></div><p className="muted">These patterns describe canonical direction and in-development product scope. They do not claim that every integration or cross-functional workflow is production-ready today.</p></div><div className="grid two-up">{solutions.map(([title,text,points])=><article className="card" key={title}><h3>{title}</h3><p>{text}</p><ul>{points.map(point=><li key={point}>{point}</li>)}</ul></article>)}</div></div></section>
  <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Cross-functional example</div><h2>“Launch a new SaaS product.”</h2></div><p className="muted">Canonical direction / In development. This sequence illustrates composition, not a claim that the complete flow is generally available in production.</p></div><div className="runtime-line">{launchFlow.map((step,index)=><div key={step}><span>{String(index+1).padStart(2,"0")}</span><strong>{step}</strong></div>)}</div></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Operating model</div><h2>One authority from request to accepted outcome.</h2></div><p className="muted">The Enterprise Operating Layer is workflow composition above the canonical Core — not a second orchestrator, router, policy engine or runtime.</p></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Current reality</div><h2>Capability names do not equal deployment evidence.</h2></div><div><p className="lead small">Finance and cost intelligence do not imply banking, accounting or an autonomous CFO. Commerce and sales do not imply verified CRM, payment or autonomous sales authority.</p><p className="muted">Production claims require implementation, tests, CI, runtime, deployment and end-to-end evidence for the specific capability being claimed.</p><div className="actions"><Link className="button secondary" href="/capabilities">Capabilities</Link><Link className="button secondary" href="/architecture">Architecture</Link><Link className="text-link" href="/trust">Trust Center →</Link></div></div></div></section>
</>}
