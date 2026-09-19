// metadata: see ./metadata.ts
"use client";
// Importers/callers: Imported by FactoriesPage.tsx
// Affected API: React component using next/link
// Data schemas: Props (none)
// User's verbatim instruction: Redesign the entire ILAIOS website to a world-class, premium technology product standard while strictly preserving the canonical brand identity defined in brand/manifest.yaml and brand/README.md. Elevate layout, typography, spacing, components, sections, cards, diagrams, interactions, animations, responsive behavior, and information presentation for both EN/TR and light/dark themes.

import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const stages = [
  ["01", "Define a bounded objective", "Create a named plan with explicit non-empty steps rather than allowing an open-ended personal automation request."],
  ["02", "Use draft-only actions", "The current implementation allows calendar, checklist, email, note and reminder drafts only."],
  ["03", "Hash payloads", "Each step retains a SHA-256 digest of its payload so the review projection can preserve deterministic evidence without silently changing content."],
  ["04", "Fail closed on unsafe actions", "Unsupported actions, duplicate step IDs, missing plans and invalid state transitions stop instead of broadening authority."],
  ["05", "Approve for review", "A plan must receive an explicit approver before its review projection becomes available."],
  ["06", "No external account mutation", "The current foundation explicitly forbids applying the plan to external personal systems or accounts."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Personal Operations Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Personal automation plans that remain reviewable before they touch anything external.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Personal Operations Factory is a bounded implemented foundation for deterministic review-only plans. It supports a small set of draft actions, hashes step payloads, requires explicit review approval and forbids direct mutation of external personal systems.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Bounded implemented foundation with deterministic evidence and approval gates. External account mutation (email, calendar, reminders) remains outside this bounded factory.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Review-first personal operations</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Automation intent does not automatically become account authority.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">The current implementation does not send emails, create calendar events, modify reminders or write to external accounts. It prepares bounded draft plans for review.</p>
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
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Trusted evidence and explicit review gates come before any external action.</h2>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Explicit human boundary</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Draft, evidence and approval stay visible before any future external execution path.</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <motion.a
            key="all-factories-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            href="/factories"
          >
            All factories
          </motion.a>
          <motion.a
            key="individuals-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/individuals"
          >
            For individuals
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
