"use client";
import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const stages = [
  ["01", "Register trusted evidence", "Store explicit source locators and SHA-256 digests; untrusted or unknown evidence cannot support a proposal."],
  ["02", "Define objective and audience", "A plan records its objective, audience and bounded channels instead of implying broad marketing authority."],
  ["03", "Use allowed draft channels", "The implemented foundation allows content drafts, email drafts, social drafts and sales-enablement proposals only."],
  ["04", "Block paid spend", "Any non-zero paid-spend request fails closed; billing, ad buying and budget mutation are outside this bounded factory."],
  ["05", "Approve for review", "A deterministic plan digest is retained and the proposal must be explicitly approved before a review projection is available."],
  ["06", "No publishing mutation", "External commerce or growth mutation is explicitly forbidden by the current implementation."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Commerce & Growth Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Evidence-backed growth proposals without hidden spend or publishing authority.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Commerce & Growth Factory is a bounded implemented foundation. It creates deterministic review-only growth plans from trusted evidence, limits channels to supported draft and sales-enablement outputs, requires approval for review and rejects paid spend or external mutation.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Implemented review-only foundation with deterministic evidence gates. Paid spend, ad execution, publishing and external mutation remain outside this bounded factory.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Review-only growth workflow</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Planning is separated from spending, publishing and account mutation.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">This foundation does not claim ad-network execution, automatic outreach, billing authority or autonomous campaign publishing.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Bounded by design</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Trusted evidence and explicit review gates come before any external action.</h2>
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
            key="security-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/security"
          >
            Security model
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
