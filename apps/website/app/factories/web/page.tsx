// metadata: see ./metadata.ts
"use client";
// Importers/callers: Imported by FactoriesPage.tsx
// Affected API: React component using next/link and ThemedDiagram
// Data schemas: Props (none)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../../CanonicalSystemDetail";
import ThemedDiagram from "../../ThemedDiagram";
import { motion } from "motion/react";


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
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Web Factory</div>
      <h1 className="text-4xl font-bold tracking-tighter mb-4 text-white">The target outcome is a verified finished website, not a mockup or partial generation.</h1>
      <p className="text-base leading-relaxed mb-6 text-gray-300">Web Factory is the canonical ILAIOS workflow for turning a business goal into a complete website lifecycle with context-derived design, implementation, independent quality gates, bounded repair and evidence.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Repository-bounded Web production and governed Vercel delivery boundaries are evidence-backed. The current exact master on the canonical public domain remains a separate production proof.</p>
      </div>
    </motion.div>
  </section>
  <section className="section surface-section factory-visual-section pt-20 pb-20">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Web Factory at a glance</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Build new websites. Upgrade existing ones. Create desktop-style web products.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The diagram is a public product explanation. “Production-ready” describes the target artifact; current public deployment status remains evidence-gated separately.</p>
        <ThemedDiagram light="/visuals/web-light.avif" dark="/visuals/web-dark.avif" alt="ILAIOS Web Factory diagram showing request, analysis, build or upgrade, verification and delivery for websites, upgrades and web apps" caption="Target workflow: request → analyze → build or upgrade → verify → deliver. Public release still requires exact deployment evidence." />
      </div>
    </motion.div>
  </section>
  <section className="section pt-20 pb-20">
    <div className="shell split-copy gap-10">
      <div>
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Product truth</div>
          <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">Canonical target and current release state remain separate.</h2>
        </div>
        <p className="text-base leading-relaxed mb-4 text-gray-300">The finished-product target includes deployable site artifacts plus required QA and evidence. The existence of this canonical workflow does not claim every stage is generally available as a public service today.</p>
        <p className="text-base leading-relaxed mb-4 text-gray-400">Current capability maturity is determined by repository implementation, tests, CI, runtime and deployment evidence.</p>
      </div>
      <div>
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Planned capability pack</div>
          <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">3D / Motion Web, inside the same governed Web Factory.</h2>
          <div className="flex items-center gap-4 mb-4">
            <span className="availability-chip is-development px-2 py-1 text-xs font-medium bg-gray-700 text-gray-400">Planned</span>
            <small className="text-sm leading-none text-gray-300">No general production-readiness claim until implementation, browser/device performance, accessibility and release evidence pass.</small>
          </div>
        </div>
        <p className="text-base leading-relaxed mb-4 text-gray-300">Rich motion should be an optional Web Factory capability, not a second web engine. The same policy, validation, evidence and release boundaries remain authoritative.</p>
        <div className="grid gap-6">
          {motionGroups.map(([title, text]) => (
            <article key={title} className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
              <h3 className="text-lg font-semibold mb-2 text-white">{title}</h3>
              <p className="text-base leading-relaxed text-gray-300">{text}</p>
            </article>
          ))}
        </div>
        <div className="callout bg-gray-700 border border-gray-600 rounded-lg p-6 mt-6">
          <div className="flex items-start gap-2 mb-2">
            <span className="eyebrow text-sm tracking-wider text-gray-400">Progressive enhancement first</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">Immersive when the device can support it. Usable when it cannot.</h2>
          <p className="text-base leading-relaxed text-gray-400">The acceptance contract must include graceful 2D fallback, mobile/touch behavior, performance budgets, keyboard/content accessibility and <code>prefers-reduced-motion</code> behavior before any 3D/Motion result is accepted.</p>
          <div className="actions flex items-center gap-4">
            <Link href="/use-ilaios" className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200">
              How to use ILAIOS
            </Link>
            <Link href="/platform/evidence" className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200">
              Evidence model
            </Link>
          </div>
        </div>
      </div>
    </div>
  </section>
  <section className="section pt-20 pb-20">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Canonical production sequence</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Design and acceptance are first-class stages.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The workflow explicitly includes research, visual direction, browser QA, visual QA, acceptance, bounded repair and deployment validation.</p>
        <div className="grid two-up gap-8">
          {stages.map(([n, t, x]) => (
            <motion.div
              key={n}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: stages.findIndex(([, tItem]) => tItem === t) * 0.1 } }}
              className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
            >
              <div className="flex items-start gap-2">
                <span className="text-xs font-bold text-gray-400">{n}</span>
                <div>
                  <strong className="text-base font-semibold text-white">{t}</strong>
                  <p className="text-base leading-relaxed text-gray-300">{x}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  </section>
  <section className="section surface-section pt-20 pb-20">
    <div className="shell">
      <div className="section-heading">
        <div className="eyebrow text-sm tracking-wider text-gray-400">Full lifecycle</div>
        <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">The canonical chain makes every quality gate visible.</h2>
      </div>
      <p className="text-base leading-relaxed text-gray-300">Website Goal → Research → Information Architecture → Copy → Design System → Visual Design → Implementation → Browser QA → Security QA → Accessibility → Performance → SEO → Visual QA → Acceptance → bounded repair → Deployment Validation → Finished Website + Evidence.</p>
      <CanonicalSystemDetail locale="en" variant="web" />
    </div>
  </section>
  <section className="section pt-20 pb-20">
    <div className="shell callout bg-gray-700 border border-gray-600 rounded-lg p-6">
      <div className="flex items-start gap-2 mb-2">
        <span className="eyebrow text-sm tracking-wider text-gray-400">Native design intelligence</span>
      </div>
      <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">Dynamic means context-derived, not random and not template roulette.</h2>
      <p className="text-base leading-relaxed text-gray-400">Brand, audience, content, trust requirements, information density and device priorities shape design strategy while structured quality evidence remains authoritative.</p>
      <div className="actions flex items-center gap-4 mt-6">
        <Link href="/use-ilaios" className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200">
          How to use ILAIOS
        </Link>
        <Link href="/platform/evidence" className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200">
          Evidence model
        </Link>
      </div>
    </div>
  </section>
</>; }
