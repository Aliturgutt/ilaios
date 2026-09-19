"use client";
import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";


const stages = [
  ["01", "Authorize scope", "Accept only an explicitly authorized repository or configured localhost/test target. Scope is not inferred or widened by the security role."],
  ["02", "Static analysis", "Run bounded defensive checks for source risk, secrets, dependency/supply-chain concerns and infrastructure configuration."],
  ["03", "Web/API observation", "Validate supplied HTTP observations only for configured local/test targets; arbitrary external network scanning is outside this factory boundary."],
  ["04", "Classify findings", "Keep finding type, severity context, affected target and evidence reviewable instead of reducing security to a model-generated verdict."],
  ["05", "Remediate inside authority", "Propose or execute only the bounded remediation allowed by the active workflow and permission model."],
  ["06", "Retest", "Repeat the applicable deterministic checks after remediation and keep the before/after evidence linked."],
  ["07", "Verify independently", "Security verification remains separate from the role that produced or remediated the finding."],
  ["08", "Stop or deliver", "Fail closed on missing authorization or unresolved gates; deliver reviewable findings and evidence when acceptance criteria pass."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Security Factory</div>
      <h1 className="text-5xl font-bold tracking-tighter mb-4 text-white">Bounded defensive security analysis with authorization, evidence and verifier separation.</h1>
      <p className="text-base leading-relaxed max-w-2xl mb-6 text-gray-300">Security Factory is a verified bounded defensive factory in the ILAIOS repository. It combines authorized code, secret, supply-chain, infrastructure and local/test web-security checks with remediation, retest and independent verification boundaries.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Verified bounded defensive factory with authorization, remediation, retest and independent verification boundaries. Arbitrary external network scanning, exploitation, or implied certifications remain outside this bounded factory.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Defensive boundary</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4">Security capability does not mean unrestricted scanning authority.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The current verified factory is deliberately fail-closed. It does not exploit arbitrary systems, authorize external penetration testing, or imply SOC 2, ISO 27001 or other external certification.</p>
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
                  <strong className="text-lg font-semibold">{t}</strong>
                  <p className="text-base leading-relaxed mt-2">{x}</p>
                </div>
              </div>
            </motion.div>
          ))}
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
        <div className="section-heading">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Security governance</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4">Permissions, DLP, evidence and independent verification remain part of the same control chain.</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-8">
          <motion.a
            key="security-model-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            href="/security"
          >
            Security model
          </motion.a>
          <motion.a
            key="permissions-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/security/permissions"
          >
            Permission boundaries
          </motion.a>
          <motion.a
            key="agents-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
            className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/agents"
          >
            Agent organization →
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }
