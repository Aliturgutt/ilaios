import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Web Factory",
  description: "How ILAIOS Web Factory structures website work from requirements and information architecture through responsive implementation, validation, security, SEO, performance, and deployment readiness.",
  alternates: { canonical: "/factories/web", languages: { en: "/factories/web", tr: "/tr/factories/web", "x-default": "/factories/web" } },
};

const stages = [
  ["01", "Goal & requirements", "Define audience, business objective, content boundaries, functional needs, constraints, and acceptance criteria."],
  ["02", "Information architecture", "Turn requirements into navigation, page hierarchy, user journeys, content structure, and responsive behavior."],
  ["03", "Content & design system", "Prepare truthful product/company content and a consistent visual system without inventing claims, customers, certifications, or availability."],
  ["04", "Implementation", "Build semantic responsive pages and interactions with accessible, maintainable web primitives."],
  ["05", "Quality & security", "Check links, forms, browser behavior, accessibility, visual consistency, security boundaries, privacy/legal surfaces, and spam/abuse controls where applicable."],
  ["06", "SEO & performance", "Validate metadata, headings, canonical/hreflang, sitemap/robots, internal links, image delivery, and performance-sensitive implementation."],
  ["07", "Deployment readiness", "Prepare domain/DNS/TLS, build, deployment, rollback, monitoring, analytics/consent where required, and production smoke verification."],
  ["08", "Evidence & maintenance", "Keep validation outcomes, versioned artifacts, deployment evidence, rollback context, and an update strategy appropriate to the site."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Web Factory</div><h1>Website production as a governed workflow, not a one-shot generation.</h1><p className="lead">Web Factory is the ILAIOS capability direction for turning a business goal into a structured website lifecycle: requirements, information architecture, content, implementation, validation, deployment preparation, and evidence.</p></section>
  <section className="section"><div className="shell"><p className="muted">Capability maturity and release state are tracked separately. This page describes the canonical workflow and does not imply every Web Factory function is generally available today.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Shared ILAIOS controls</div><h2>Authorization, validation, evidence, and recovery remain part of the workflow.</h2></div><div className="actions"><Link className="button" href="/how-it-works">How ILAIOS works</Link><Link className="button secondary" href="/capabilities">All capabilities</Link></div></div></section>
</>; }
