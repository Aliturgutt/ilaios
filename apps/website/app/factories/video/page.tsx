// metadata: see ./metadata.ts
"use client";
// Importers/callers: Imported by FactoriesPage.tsx
// Affected API: React component using next/link and ThemedDiagram
// Data schemas: Props (none)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";
import { motion } from "motion/react";


const stages = [
  ["01", "Topic & research", "Start from a defined content goal, gather relevant research, and preserve source context where the workflow depends on factual claims."],
  ["02", "Content & script planning", "Turn the brief into a structured content plan, script, continuity constraints, and acceptance requirements."],
  ["03", "Scene & shot planning", "Break the script into scenes and shots with duration, composition, continuity, asset, and generation requirements."],
  ["04", "Asset & execution planning", "Plan uploaded/generated assets, rights/provenance, quality/cost thresholds and eligible execution resources inside policy."],
  ["05", "Media, voice & audio", "Acquire or generate visual media, voice, audio, and captions through bounded job steps."],
  ["06", "Assembly & rendering", "Compose the media artifact, render through the admitted technical profile, and retain artifact identity."],
  ["07", "Technical & content validation", "Check media properties, continuity/content requirements, policy and rights constraints, and required acceptance criteria before approval."],
  ["08", "Approval & platform adaptation", "Where required, obtain approval and prepare platform-specific format, metadata, cover/thumbnail, disclosure, and scheduling data."],
  ["09", "Publish & verify", "Publishing is a side effect: use idempotency, rate-limit handling, delivery verification, duplicate prevention, and post-publish checks."],
  ["10", "Evidence, metrics & recovery", "Retain provenance, validation, delivery state, cost, retry/recovery context, and metrics without treating provider-reported success as final proof."],
] as const;

const referenceGroups = [
  ["Native reference path", "A Desktop-uploaded photo, product or logo stays tenant-bound, passes governed reference admission, and can be relayed through a short-lived secure URL to an eligible native reference input or frame-reference path."],
  ["Identity & product consistency QA", "Generated video is checked against the admitted references so supported visual identity, subject appearance, product geometry, colors, materials and marks do not silently drift."],
  ["Strict logo fidelity", "Native reference comes first. Logo consistency QA follows. If a logo must remain exact, the strongest target is deterministic original-asset lock/overlay or compositing, then final QA on the exact rendered artifact."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Video / Media Factory</div>
      <h1 className="text-4xl font-bold tracking-tighter mb-4 text-white">A media lifecycle that remains controlled from references to delivery.</h1>
      <p className="text-base leading-relaxed mb-6 text-gray-300">Video / Media Factory coordinates the content-production chain while keeping validation, evidence, recovery, publishing side effects, and cost controls explicit.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Repository evidence includes a real finished-product Video E2E path with independent acceptance. Live zero-cost external provider availability is still not verified and must fail closed when no eligible route exists.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Video / Media Factory at a glance</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Turn references into a reviewable, verified media target.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The visual describes the target production path. A “verified video” label means required acceptance checks must pass for that exact artifact; it is not a promise that every external generation route is currently available.</p>
        <ThemedDiagram light="/visuals/video-light.avif" dark="/visuals/video-dark.avif" alt="ILAIOS Video and Media Factory diagram showing request, reference analysis, production, verification and delivery" caption="Target workflow: request → analyze references → produce → verify → deliver. External generation and publishing remain separately evidence-gated." />
      </div>
    </motion.div>
  </section>
  <section className="section pt-20 pb-20">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Native reference & identity consistency</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Use real photos and brand assets to preserve people, products and logos across generated video.</h2>
        </div>
        <div className="flex items-center gap-4 mb-4">
          <span className="availability-chip is-development px-2 py-1 text-xs font-medium bg-gray-700 text-gray-400">In development</span>
          <small className="text-sm leading-none text-gray-300">Authenticated reference upload/binding and reference-aware conditioning exist in the repository; native signed relay, direct provider-reference delivery, full consistency QA and live certification remain separately evidence-gated.</small>
        </div>
      </div>
      <p className="text-base leading-relaxed mb-6 text-gray-300">The public experience stays simple: attach a reference and describe the outcome. Provider-specific input-reference and frame-image contracts remain behind the governed product boundary.</p>
      <div className="grid gap-6">
        {referenceGroups.map(([title, text]) => (
          <article key={title} className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale">
            <h3 className="text-lg font-semibold mb-2 text-white">{title}</h3>
            <p className="text-base leading-relaxed text-gray-300">{text}</p>
          </article>
        ))}
      </div>
      <div className="callout bg-gray-700 border border-gray-600 rounded-lg p-6 mt-6">
        <div className="flex items-start gap-2 mb-2">
          <span className="eyebrow text-sm tracking-wider text-gray-400">Target governed chain</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">Reference → secure relay → native conditioning → generation → consistency QA → logo asset-lock when required → final QA & evidence.</h2>
        <p className="text-base leading-relaxed text-gray-400 mb-4">Real generation, CI and live production certification must prove the exact provider path and final artifact before this capability is promoted beyond its evidence-backed maturity.</p>
        <div className="actions flex items-center gap-4 mt-6">
          <Link href="/use-ilaios" className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200">
            How to use ILAIOS
          </Link>
          <Link href="/platform/evidence" className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200">
            Evidence model
          </Link>
        </div>
      </div>
    </motion.div>
  </section>
  <section className="section pt-20 pb-20">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="grid two-up gap-8">
          {stages.map(([n, t, x], index) => (
            <motion.div
              key={n}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
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
  <section className="section pt-20 pb-20">
    <div className="shell callout bg-gray-700 border border-gray-600 rounded-lg p-6">
      <div className="flex items-start gap-2 mb-2">
        <span className="eyebrow text-sm tracking-wider text-gray-400">Provider-independent by design</span>
      </div>
      <h2 className="text-2xl font-bold tracking-tighter mb-2 text-white">Execution resources can change without becoming the source of workflow authority.</h2>
      <p className="text-base leading-relaxed text-gray-400 mb-4">The public product experience does not require users to choose a provider. Eligibility, policy, cost and quality remain governed behind the product boundary.</p>
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
