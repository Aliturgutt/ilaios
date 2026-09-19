"use client";
// Importers/callers: Imported by FactoriesPage.tsx (likely)
// Affected API: React component using next/link and react hooks (useState, useRef) - actually no hooks used, just next/link and ThemedDiagram
// Data schemas: Props (none)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";
import { motion } from "motion/react";


const stages = [
  ["01", "Specify", "Define the requested outcome, repository or system boundary, constraints, acceptance criteria, risk, and required evidence."],
  ["02", "Plan", "Decompose work into bounded engineering jobs with dependencies, ownership, permissions, and a validation plan."],
  ["03", "Inspect before changing", "Use source, symbol, dependency, configuration, and runtime context where available instead of making blind edits."],
  ["04", "Implement inside scope", "Engineering capabilities modify only authorized files and systems; architecture and security boundaries remain authoritative."],
  ["05", "Test & review", "Run applicable deterministic tests, lint/type/static checks, code review, and security checks before acceptance."],
  ["06", "Verify independently", "Material work is not accepted solely because its author or executing process reports success. Required independent verification remains risk-driven."],
  ["07", "Release preparation", "Version artifacts, capture build/test/security evidence, prepare rollback or recovery semantics, and keep environment progression explicit."],
  ["08", "Deliver & reconcile", "Deliver source/build/deployment preparation with traceable evidence; failures follow bounded diagnose, repair, retest, retry, or rollback paths."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Software Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Software engineering with explicit boundaries and acceptance gates.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Software Factory converts software goals into governed engineering work rather than treating code generation as an unrestricted one-shot request.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Bounded local Windows finished-product scope is repository-verified. Arbitrary external-repository effects, software breadth and commercial release are not implied by that evidence.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Software Factory at a glance</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Turn requirements into tested, reviewable software changes.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The target visual keeps requirements, implementation, tests, review, bounded repair and handoff visible without treating a code diff as completion.</p>
        <ThemedDiagram light="/visuals/software-light.avif" dark="/visuals/software-dark.avif" alt="ILAIOS Software Factory diagram showing requirement and context, scope and plan, implementation, tests, review, bounded repair and tested change" caption="Target workflow: requirement + context → scope & plan → implement → test → review → bounded repair → tested change." />
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
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Trusted evidence and explicit verification gates come before any external action.</h2>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Governed delivery</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Implementation, verification, merge and release authority remain separate where risk requires it.</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <motion.a
            key="use-ilaios-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            href="/use-ilaios"
          >
            How to use ILAIOS
          </motion.a>
          <motion.a
            key="validation-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/platform/validation"
          >
            Validation model
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
