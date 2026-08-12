import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ILAIOS Factories",
  description: "Explore ILAIOS governed production and operations factories, including web, software, media, security, research, documents, growth and personal operations.",
  alternates: { canonical: "/factories", languages: { en: "/factories", tr: "/tr/factories", "x-default": "/factories" } },
};

const factories = [
  ["Web Factory", "Governed website production from requirements and information architecture through validation and deployment preparation.", "/factories/web"],
  ["Software Factory", "Bounded engineering workflows with deterministic quality gates and traceable delivery context.", "/factories/software"],
  ["Video / Media Factory", "Structured media production across planning, assets, render, validation and publishing preparation.", "/factories/video"],
  ["Security Factory", "Authorized defensive analysis with explicit scope, remediation evidence and independent verification boundaries.", "/factories/security"],
  ["Research & Data Factory", "Provenance-first research that separates proposed claims from verified facts and deterministic bounded analysis.", "/factories/research-data"],
  ["Creative & Document Factory", "Trusted-source document composition with deterministic hashes and approval-gated export projections.", "/factories/creative-document"],
  ["Commerce & Growth Factory", "Evidence-backed review-only growth proposals with bounded draft channels and no paid-spend or publishing authority.", "/factories/commerce-growth"],
  ["Personal Operations Factory", "Review-only personal operation plans for draft actions such as checklists, reminders, notes, calendar and email drafts.", "/factories/personal-operations"],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Factories</div><h1>Specialized production and operations workflows under one governance model.</h1><p className="lead">ILAIOS factories turn different kinds of work into bounded workflows rather than unconstrained one-shot generation. Each detail page states what is implemented, what must be approved, and what the current foundation explicitly does not do.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Factory map</div><h2>Choose the work domain, then inspect its controls and boundaries.</h2></div><p className="muted">Factory maturity is not implied by the name. Public pages distinguish bounded implemented foundations from broader product workflows and do not claim external mutation, publishing, spend or availability where repository evidence does not support it.</p></div><div className="grid two-up">{factories.map(([title,text,href]) => <Link className="detail-link-card" href={href} key={href}><span>Factory</span><h3>{title}</h3><p>{text}</p><strong>Explore →</strong></Link>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Governed by the same Core</div><h2>Authority, validation, evidence and recovery remain separate from model narration.</h2></div><div className="actions"><Link className="button" href="/core">Explore Core</Link><Link className="button secondary" href="/capabilities">Capability map</Link></div></div></section>
</>; }
