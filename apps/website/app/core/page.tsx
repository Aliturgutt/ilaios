import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "ILAIOS Core", description: "Understand the ILAIOS Core control, validation, evidence and recovery model.", alternates: { canonical: "/core", languages: { en: "/core", tr: "/tr/core", "x-default": "/core" } } };

const flow = [
  ["01", "Goal & context", "The requested result enters with the identity, project context and limits that define the operating boundary."],
  ["02", "Control", "Policy, permissions and approvals decide what the work is allowed to do before sensitive execution."],
  ["03", "Plan & execute", "The work is decomposed and routed to bounded capabilities; a model or agent name is never authority by itself."],
  ["04", "Verify & deliver", "Acceptance checks, evidence and bounded recovery decide whether the result is ready to deliver."],
] as const;

export default function Page(){ return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">ILAIOS Core</div><h1>One control authority around every governed execution.</h1><p className="lead">Core connects the requested outcome to permissions, bounded execution, verification, evidence and recovery without handing system authority to a model, agent or provider.</p><div className="actions"><Link className="button" href="/capabilities">Explore capabilities</Link><Link className="button secondary" href="/architecture">See the architecture</Link></div></section>
  <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">Controlled path</div><h2>From intent to an accepted result.</h2></div></div><div className="audience-process">{flow.map(([n,title,text])=><article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell audience-focus"><div><span className="micro-label">Core principle</span><h2>Execution resources can change. Authority does not.</h2></div><div className="audience-outcome-list"><article><span>01</span><div><strong>Single control boundary</strong><p>Identity, policy, approvals and permitted actions remain explicit and centralized.</p></div></article><article><span>02</span><div><strong>Bounded execution</strong><p>Agents, skills, tools and providers operate only inside the scope granted to the job.</p></div></article><article><span>03</span><div><strong>Independent acceptance</strong><p>Validation and required approvals determine whether produced work can advance.</p></div></article><article><span>04</span><div><strong>Evidence and recovery</strong><p>Material state, provenance and failure handling stay reviewable when work succeeds or fails.</p></div></article></div></div></section>
</>; }
