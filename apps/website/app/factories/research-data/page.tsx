import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Research & Data Factory",
  description: "ILAIOS Research & Data Factory is a bounded provenance-first workflow for registering sources, validating claims, deterministic numeric analysis and projecting only verified facts into knowledge structures.",
  alternates: { canonical: "/factories/research-data", languages: { en: "/factories/research-data", tr: "/tr/factories/research-data", "x-default": "/factories/research-data" } },
};

const stages = [
  ["01", "Register evidence", "Accept explicitly supplied source content with a locator, stable source ID, trust flag, metadata and SHA-256 content digest."],
  ["02", "Propose a claim", "Keep a claim separate from fact status and require it to reference known source IDs instead of relying on unsupported model narration."],
  ["03", "Verify support", "Require the configured minimum of trusted independent sources before a claim may become verified; the default bounded implementation requires two."],
  ["04", "Fail closed", "Unknown sources, duplicate evidence IDs, insufficient trusted support and invalid analysis inputs stop the workflow rather than silently weakening the gate."],
  ["05", "Analyze deterministically", "For bounded numeric inputs, retain a canonical values digest with count, minimum, maximum and mean so repeated analysis is reproducible."],
  ["06", "Project verified knowledge", "Only verified claims may project as Fact nodes, with Evidence nodes and explicit derived-from edges preserving provenance."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Research & Data Factory</div><h1>Research that keeps claims, sources and verification boundaries visible.</h1><p className="lead">Research & Data Factory is a bounded implemented foundation in the ILAIOS repository. It records source provenance, separates proposed claims from verified facts, performs deterministic bounded numeric analysis and fails closed when evidence requirements are not met.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Provenance-first</div><h2>A research output does not become a fact merely because a model produced it.</h2></div><p className="muted">The current implementation does not autonomously crawl arbitrary external sources or imply general-purpose research coverage. It operates on explicitly supplied evidence and promotes claims only when configured trusted-source gates pass.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Connected knowledge</div><h2>Verified facts remain linked to the evidence from which they were derived.</h2></div><div className="actions"><Link className="button" href="/capabilities">Explore capabilities</Link><Link className="button secondary" href="/core">Explore ILAIOS Core</Link><Link className="text-link" href="/architecture">Architecture →</Link></div></div></section>
</>; }
