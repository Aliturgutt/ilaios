import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Agent Organization",
  description: "How ILAIOS governs specialist agent identities, teams, capabilities, permissions, verifier separation and runtime readiness without treating agent names as authority.",
  alternates: { canonical: "/agents", languages: { en: "/agents", tr: "/tr/agents", "x-default": "/agents" } },
};

const teams = [
  ["Core", "Orchestrator, Planner, Supervisor, Policy and CostResource coordinate planning, governance and resource boundaries."],
  ["Engineering", "Architecture, core, frontend, backend, integration, testing, code review, runtime QA, release assessment and recovery roles."],
  ["Security", "Defensive coordinator, code, web/API, supply-chain, infrastructure and independent verification roles."],
  ["Web", "UX, visual, asset, content, SEO and browser-QA roles for governed website workflows."],
  ["Media", "Story, scene direction, media generation, voice/audio, editing, QA, social metadata and publishing roles."],
  ["Intelligence", "Research, fact checking, data analysis and knowledge roles."],
  ["Operations", "Automation, analytics, monitoring, recovery, provider watching and benchmarking roles."],
  ["Meta", "Independent verification and controlled self-development coordination roles."],
] as const;

const rules = [
  ["Stable machine identity", "Orchestration binds to stable ilaios.agent.* machine IDs, capability contracts and permissions. Human-readable aliases are presentation metadata."],
  ["Names are not authority", "An agent name never grants permission. Callers, targets, execution grants, policy and security controls determine what may run."],
  ["Verifier separation", "No agent independently verifies itself, and implementation roles cannot promote their own output to VERIFIED or PRODUCTION."],
  ["Readiness is evidence-driven", "REGISTERED means governed identity and manifest exist. Specialized executor readiness requires separate bounded runtime and end-to-end evidence."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS agent organization</div><h1>Specialist roles behind stable identities, explicit permissions and independent verification.</h1><p className="lead">ILAIOS uses a governed multi-team agent organization, but orchestration does not depend on a name or persona. Machine IDs, capability contracts, permissions, allowed callers and targets, escalation paths and verifier identities remain authoritative.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Teams</div><h2>Specialization is organized by responsibility, not unrestricted autonomy.</h2></div><p className="muted">The repository governs named specialist registrations across these teams. Registration proves identity/governance metadata; it does not by itself claim that every specialist has a verified provider-backed executor.</p></div><div className="grid two-up">{teams.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Authority model</div><h2>Agents operate inside the platform control model.</h2></div></div><div className="grid two-up">{rules.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><div className="actions"><Link className="button" href="/how-it-works">How ILAIOS works</Link><Link className="button secondary" href="/security/permissions">Permission model</Link><Link className="text-link" href="/platform/evidence">Evidence model →</Link></div></div></section>
</>; }
