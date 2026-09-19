"use client";
import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const steps = [
  ["01", "Describe what you want finished", "Start with the outcome, references and constraints. You do not need to choose the internal model, agent or provider stack."],
  ["02", "ILAIOS organizes the work", "The system turns the request into bounded work and applies the permissions, policy and approvals required for that work."],
  ["03", "The work is produced", "The applicable capabilities execute the admitted work across web, software, media, research or a combination of them."],
  ["04", "ILAIOS verifies and delivers", "Required checks decide whether the result is accepted. If it passes, the finished result and its evidence are delivered; unresolved work does not become success by narrative."],
] as const;

const verified = [
  ["Works", "The required function or outcome is actually present."],
  ["Fits", "The result is checked against the stated acceptance criteria."],
  ["Safe", "Applicable policy, security and permission checks remain satisfied."],
  ["Traceable", "The accepted result retains the evidence needed to review what was delivered."],
] as const;

export default function Page() {
  return <>
    <section className="shell page-hero compact-page-hero pt-16 pb-16">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="eyebrow text-sm tracking-wider text-gray-400">How ILAIOS Works</div>
        <h1 className="text-5xl font-semibold tracking-tighter mb-6">Say what you need. ILAIOS manages the work to a verified result.</h1>
        <p className="text-xl leading-relaxed mb-8 text-gray-300">The public experience is intentionally simple: describe the finished outcome, let ILAIOS govern and execute the work, then receive the result only after the required checks pass.</p>
        <div className="actions flex items-center gap-4">
          <Link className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href="/use-ilaios">
            Use ILAIOS
          </Link>
        </div>
      </motion.div>
    </section>
    <section className="section pt-20 pb-20">
      <div className="shell">
        <div className="section-heading">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">Four steps</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">From one outcome to finished work.</h2>
          </div>
          <p className="text-base leading-relaxed mb-8 text-gray-300">No provider selection, worker IDs or internal routing decisions are required from the user.</p>
        </div>
        <div className="journey-grid grid gap-6 pt-8">
          {steps.map(([n,t,x], index) => (
            <article key={n} className="journey-card border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
              <motion.div
                initial={{ x: -20, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1], delay: index * 0.1 } }}
              >
                <span className="text-xs font-bold text-gray-400">{n}</span>
                <h3 className="text-lg font-semibold mb-2 text-white">{t}</h3>
                <p className="text-base leading-relaxed text-gray-300">{x}</p>
              </motion.div>
            </article>
          ))}
        </div>
      </div>
    </section>
    <section className="section surface-section pt-20 pb-20 bg-gray-800">
      <div className="shell">
        <div className="section-heading">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">Product flow</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">Goal → governed work → production → verification → delivery.</h2>
          </div>
          <p className="text-base leading-relaxed mb-6 text-gray-300">This is the user-facing product path. Internal provider and execution details remain behind the product boundary.</p>
        </div>
        <div className="runtime-line grid gap-6 pt-8">
          {steps.map(([n,t]) => (
            <div key={n} className="flex flex-col items-start gap-2">
              <span className="text-xs font-semibold text-gray-400">{n}</span>
              <strong className="text-lg font-semibold text-white">{t}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
    <section className="section pt-20 pb-20">
      <div className="shell">
        <div className="section-heading">
          <div>
            <div className="eyebrow text-sm tracking-wider text-gray-400">What verified means</div>
            <h2 className="text-3xl font-semibold tracking-tighter mb-4">Verification answers a practical question: is this result ready to accept?</h2>
          </div>
          <p className="text-base leading-relaxed mb-8 text-gray-300">The exact checks depend on the work being produced. Required acceptance checks cannot be skipped just to call the work finished.</p>
        </div>
        <div className="journey-grid grid gap-6 pt-8">
          {verified.map(([title,text],i)=> (
            <article key={title} className="journey-card border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
              <span className="text-xs font-bold text-gray-400">{String(i+1).padStart(2,"0")}</span>
              <h3 className="text-lg font-semibold mb-2 text-white">{title}</h3>
              <p className="text-base leading-relaxed text-gray-300">{text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
    <section className="section compact-section pt-20 pb-20">
      <div className="shell callout flex flex-col items-center gap-4 text-center bg-gray-800">
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">Need the technical model?</div>
          <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">The public flow stays simple; the architecture remains inspectable.</h2>
          <p className="text-base leading-relaxed text-gray-300">Architecture, Core and Security explain the control and evidence model without forcing those internal details into the main product journey.</p>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <Link className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href="/architecture">
            Architecture
          </Link>
          <Link className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200" href="/core">
            Core
          </Link>
        </div>
      </div>
    </section>
  </>
}
