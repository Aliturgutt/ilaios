import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Solutions", description: "Explore ILAIOS solution patterns for governed research, enterprise intelligence, business operations and digital production.", alternates: { canonical: "/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Launch a digital product", "Move from research and planning into the website, software, application or media work the launch actually needs."],
  ["Produce and update digital assets", "Coordinate web, software and media deliverables without making the user operate a separate AI workflow for every output."],
  ["Research before acting", "Keep sources, uncertainty and verification visible when a decision or production task depends on external information."],
  ["Automate repeatable work", "Combine deterministic steps and intelligent capabilities while permissions, approvals and acceptance remain explicit."],
] as const;

const operatingModel = [
  ["01", "Describe the outcome", "Start from the result, not from a list of tools."],
  ["02", "Resolve the work", "ILAIOS identifies the capabilities and production paths that apply."],
  ["03", "Execute within limits", "Identity, policy, approvals and bounded tools constrain admitted work."],
  ["04", "Verify before delivery", "Acceptance checks determine whether the result can be returned as finished."],
] as const;

export default function Solutions(){return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">Solutions</div><h1>Start with the outcome, not the toolchain.</h1><p className="lead">ILAIOS is designed to coordinate the research, planning, production and verification a goal requires under one governed product boundary.</p><div className="actions"><Link className="button" href="/use-ilaios">Explore how to use ILAIOS</Link></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Outcome patterns</div><h2>Different goals can reuse the same controlled execution model.</h2></div><p className="muted">These examples describe product direction and are not claims that every integration or end-to-end path is generally available today.</p></div><div className="principle-directory">{solutions.map(([title,text],index)=><article key={title}><span>{String(index+1).padStart(2,"0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">One operating model</div><h2>From requested result to verified delivery.</h2></div></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Choose the right view</div><h2>Individual and enterprise use share the platform, but not the same product story.</h2></div><div className="actions"><Link className="button secondary" href="/individuals">For individuals</Link><Link className="button secondary" href="/enterprise">For enterprises</Link><Link className="text-link" href="/trust">Trust boundary →</Link></div></div></section>
</>}
