// metadata: see ./metadata.ts
"use client";
import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const stages = [
  ["01", "Register trusted sources", "Record explicit source IDs, locators and SHA-256 content digests; source trust is retained as part of the bounded input state."],
  ["02", "Compose deterministically", "Build a text artifact from non-blank sections and known trusted source IDs, producing a stable body digest."],
  ["03", "Fail closed on provenance", "Unknown, duplicate or untrusted source references stop composition instead of silently weakening evidence requirements."],
  ["04", "Require approval", "A composed artifact remains unapproved until an explicit approval transition occurs."],
  ["05", "Export a projection", "Only approved artifacts may export a projection containing title, body, body digest and source provenance."],
  ["06", "No external mutation", "The current foundation produces deterministic text artifacts and projections; it does not publish, send or mutate external systems."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Creative & Document Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Document generation with trusted sources, deterministic provenance and an approval gate.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Creative & Document Factory is a bounded implemented foundation in the ILAIOS repository. It composes text artifacts from explicitly registered trusted sources, hashes source and body content, blocks unsupported provenance and exports only after approval.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Bounded implemented foundation with deterministic provenance and approval gates. Arbitrary format generation, external publishing and autonomous distribution remain outside this bounded factory.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Bounded document workflow</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Drafting does not silently become publication authority.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">The current implementation is intentionally narrow. It does not claim arbitrary document-format generation, external publishing or autonomous distribution.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Governed output</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Approved projections preserve the source trail used to build the artifact.</h2>
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
            key="capabilities-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/capabilities"
          >
            Capabilities
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
