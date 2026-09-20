import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../../CanonicalSystemDetail";
import ThemedDiagram from "../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Web Factory",
  description: "ILAIOS Web Factory: from goal, research and information architecture through visual design, implementation, browser/security/accessibility/performance/SEO/visual QA, bounded repair, deployment validation and finished-site evidence.",
  alternates: { canonical: "/factories/web", languages: { en: "/factories/web", tr: "/tr/factories/web", "x-default": "/factories/web" } },
};

const stages = [
  ["01", "Goal & research", "Define audience, business objective, trusted inputs, constraints, acceptance criteria and research needs."],
  ["02", "Information architecture & copy", "Create navigation, page hierarchy, journeys and truthful content without inventing claims, customers or availability."],
  ["03", "Design system & visual direction", "Derive typography, spacing, surfaces, composition, imagery, interaction and responsive strategy from project context."],
  ["04", "Implementation", "Build semantic responsive pages and interactions with accessible, maintainable web primitives."],
  ["05", "Browser & functional QA", "Check routes, links, forms, browser behavior, interactions and responsive composition."],
  ["06", "Security & accessibility QA", "Validate applicable security boundaries, privacy/legal surfaces, keyboard behavior, contrast, focus and accessible content."],
  ["07", "Performance & SEO", "Validate metadata, headings, canonical/hreflang, sitemap/robots, internal links, images and performance-sensitive implementation."],
  ["08", "Visual QA & anti-generic review", "Evaluate hierarchy, density, composition, brand coherence, repetition, mobile transformation and generic-AI design signals."],
  ["09", "Acceptance & bounded repair", "Required gates decide acceptance. Failed checks produce bounded repair and re-validation rather than self-reported success."],
  ["10", "Deployment validation & evidence", "Where deployment is requested and authorized, verify the deployed artifact and retain version, validation and rollback context."],
] as const;

const motionGroups = [
  ["Immersive scenes", "3D hero sections, scroll-driven 3D scenes, parallax and camera transitions, particle effects, WebGL backgrounds and 3D typography."],
  ["Interactive products", "Product/model rotation plus pointer, mouse and touch interaction for explorable product experiences."],
  ["Safe delivery", "Responsive 2D fallback for lower-capability devices, an explicit performance budget, accessibility controls and reduced-motion fallback."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Web Factory</div><h1>The target outcome is a verified finished website, not a mockup or partial generation.</h1><p className="lead">Web Factory is the canonical ILAIOS workflow for turning a business goal into a complete website lifecycle with context-derived design, implementation, independent quality gates, bounded repair and evidence.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Preview</span><p>Repository-bounded Web production and governed Vercel delivery boundaries are evidence-backed. The current exact master on the canonical public domain remains a separate production proof.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Web Factory at a glance</div><h2>Build new websites. Upgrade existing ones. Create desktop-style web products.</h2></div><p>The diagram is a public product explanation. “Production-ready” describes the target artifact; current public deployment status remains evidence-gated separately.</p></div><ThemedDiagram light="/visuals/web-light.avif" dark="/visuals/web-dark.avif" alt="ILAIOS Web Factory diagram showing request, analysis, build or upgrade, verification and delivery for websites, upgrades and web apps" caption="Target workflow: request → analyze → build or upgrade → verify → deliver. Public release still requires exact deployment evidence." priority /></div></section>

  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Product truth</div><h2>Canonical target and current release state remain separate.</h2></div><div><p className="lead small">The finished-product target includes deployable site artifacts plus required QA and evidence. The existence of this canonical workflow does not claim every stage is generally available as a public service today.</p><p className="muted">Current capability maturity is determined by repository implementation, tests, CI, runtime and deployment evidence.</p></div></div></section>

  <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Planned capability pack</div><h2>3D / Motion Web, inside the same governed Web Factory.</h2><div className="factory-status-row"><span className="availability-chip is-development">Planned</span><small>No general production-readiness claim until implementation, browser/device performance, accessibility and release evidence pass.</small></div></div><p>Rich motion should be an optional Web Factory capability, not a second web engine. The same policy, validation, evidence and release boundaries remain authoritative.</p></div><div className="grid">{motionGroups.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><div className="callout"><div><div className="eyebrow">Progressive enhancement first</div><h2>Immersive when the device can support it. Usable when it cannot.</h2><p className="muted">The acceptance contract must include graceful 2D fallback, mobile/touch behavior, performance budgets, keyboard/content accessibility and <code>prefers-reduced-motion</code> behavior before any 3D/Motion result is accepted.</p></div><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/platform/evidence">Evidence model</Link></div></div></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Canonical production sequence</div><h2>Design and acceptance are first-class stages.</h2></div><p className="muted">The workflow explicitly includes research, visual direction, browser QA, visual QA, acceptance, bounded repair and deployment validation.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Full lifecycle</div><h2>The canonical chain makes every quality gate visible.</h2></div><p>Website Goal → Research → Information Architecture → Copy → Design System → Visual Design → Implementation → Browser QA → Security QA → Accessibility → Performance → SEO → Visual QA → Acceptance → bounded repair → Deployment Validation → Finished Website + Evidence.</p></div><CanonicalSystemDetail locale="en" variant="web" /></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Native design intelligence</div><h2>Dynamic means context-derived, not random and not template roulette.</h2><p className="muted">Brand, audience, content, trust requirements, information density and device priorities shape design strategy while structured quality evidence remains authoritative.</p></div><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/platform/evidence">Evidence model</Link></div></div></section>
</>; }
