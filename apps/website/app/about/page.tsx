import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description: "Learn why ILAIOS is building governed infrastructure for intelligent automation.",
  alternates: { canonical: "/about", languages: { en: "/about", tr: "/tr/about", "x-default": "/about" } },
};

const principles = [
  ["Control before convenience", "Automation should not bypass authority simply because a model can act. Important operations remain bounded by policy, permissions, and explicit execution conditions."],
  ["Evidence before confidence", "A useful system should be able to show what happened, what was validated, and why an action was accepted rather than relying on confidence alone."],
  ["Architecture before interface", "Desktop, mobile, and web clients are projections of backend authority, allowing interfaces to evolve without weakening system boundaries."],
] as const;

export default function About() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">About ILAIOS</div><h1>Useful automation with clear authority.</h1><p className="lead">ILAIOS is an independent technology company building systems for governed intelligent automation. The goal is not autonomy at any cost; it is reliable execution with explicit control, evidence, and operational visibility.</p></section>
    <section className="section"><div className="shell"><div className="eyebrow">Operating principles</div><h2>Trust is an engineering property.</h2><div className="grid">{principles.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section architecture-section"><div className="shell split-copy"><div><div className="eyebrow">What we are building</div><h2>A control system for intelligent work.</h2></div><div><p className="lead small">The product direction combines governed workflows, bounded tools, intelligent capabilities, approval gates, validation, and evidence into one operational model.</p><p className="muted">ILAIOS is under active development. This website separates validated engineering direction from capabilities that have not yet been released.</p><div className="actions"><Link className="text-link" href="/platform">Explore the platform →</Link><Link className="text-link" href="/security">Security direction →</Link></div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Company direction</div><h2>Built for long-lived operational trust.</h2></div><div><p className="muted">The intended architecture keeps authority, validation, evidence, and execution contracts durable even as models, tools, interfaces, and providers evolve.</p></div></div></section>
  </>;
}
