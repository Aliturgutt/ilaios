"use client";
// Importers/callers: Imported by FactoriesPage.tsx
// Affected API: React component using next/link
// Data schemas: Props (none)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const stages = [
  ["01", "Register evidence", "Accept explicitly supplied source content with a locator, stable source ID, trust flag, metadata and SHA-256 content digest."],
  ["02", "Propose a claim", "Keep a claim separate from fact status and require it to reference known source IDs instead of relying on unsupported model narration."],
  ["03", "Verify support", "Require the configured minimum of trusted independent sources before a claim may become verified; the default bounded implementation requires two."],
  ["04", "Fail closed", "Unknown sources, duplicate evidence IDs, insufficient trusted support and invalid analysis inputs stop the workflow rather than silently weakening the gate."],
  ["05", "Analyze deterministically", "For bounded numeric inputs, retain a canonical values digest with count, minimum, maximum and mean so repeated analysis is reproducible."],
  ["06", "Project verified knowledge", "Only verified claims may project as Fact nodes, with Evidence nodes and explicit derived-from edges preserving provenance."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Research & Data Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Research that keeps claims, sources and verification boundaries visible.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Research & Data Factory is a bounded implemented foundation in the ILAIOS repository. It records source provenance, separates proposed claims from verified facts, performs deterministic bounded numeric analysis and fails closed when evidence requirements are not met.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Bounded implemented foundation with deterministic provenance and verification gates. Autonomous crawling, general-purpose research coverage and external knowledge projection remain outside this bounded factory.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Provenance-first</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">A research output does not become a fact merely because a model produced it.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">The current implementation does not autonomously crawl arbitrary external sources or imply general-purpose research coverage. It operates on explicitly supplied evidence and promotes claims only when configured trusted-source gates pass.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Bounded execution sequence</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Trusted evidence and explicit verification gates come before any knowledge projection.</h2>
        </div>
        <div className="grid two-up gap-8 pt-8">
          {stages.map(([n, t, x], index) => (
            <motion.div
              key={n}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
              className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
            >
              <div className="flex items-start gap-3">
                <span className="text-xs font-bold text-gray-400 shrink-0">{n}</span>
                <div>
                  <strong className="text-lg font-semibold text-white">{t}</strong>
                  <p className="text-base leading-relaxed mt-2 text-gray-300">{x}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  </section>
  <section className="section compact-section pt-20 pb-20">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell compact-cta text-center">
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">Connected knowledge</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Verified facts remain linked to the evidence from which they were derived.</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <motion.a
            key="capabilities-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            href="/capabilities"
          >
            Explore capabilities
          </motion.a>
          <motion.a
            key="core-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/core"
          >
            Explore ILAIOS Core
          </motion.a>
          <motion.a
            key="architecture-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
            className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/architecture"
          >
            Architecture →
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
