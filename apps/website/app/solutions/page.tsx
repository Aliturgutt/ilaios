import type { Metadata } from "next";
import Link from "next/link";
import { motion } from "motion/react";

export const metadata: Metadata = { title: "Solutions", description: "Explore ILAIOS solution patterns for governed research, enterprise intelligence, business operations and digital production.", alternates: { canonical: "/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Launch a digital product", "Move from research and planning into the website, software, application or media work the launch actually needs."],
  ["Produce and update digital assets", "Coordinate web, software and media deliverables without making the user operate a separate AI workflow for every output."],
  ["Research before acting", "Keep sources, uncertainty and verification visible when a decision or production task depends on external information."],
  ["Automate repeatable work", "Combine deterministic steps and intelligent capabilities while permissions, approvals and acceptance remain explicit."],
] as const;

const operatingModel = [
  ["01", "Describe the outcome", "Start from the result, not from a list of tools."],
  ["02", "Resolve the work", "ILAIOS identifies the capabilities and production paths that apply."],
  ["03", "Execute within limits", "Identity, policy, approvals and bounded tools constrain admitted work."],
  ["04", "Verify before delivery", "Acceptance checks determine whether the result can be returned as finished."],
] as const;

export default function Solutions(){return <>
  <section className="shell page-hero compact-page-hero">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow">Solutions</div>
      <h1>Start with the outcome, not the toolchain.</h1>
      <p className="lead">ILAIOS is designed to coordinate the research, planning, production and verification a goal requires under one governed product boundary.</p>
      <div className="actions"><Link className="button" href="/use-ilaios">Explore how to use ILAIOS</Link></div>
    </motion.div>
  </section>
  <section className="section">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Outcome patterns</div>
            <h2>Different goals can reuse the same controlled execution model.</h2>
          </div>
          <p className="muted">These examples describe product direction and are not claims that every integration or end-to-end path is generally available today.</p>
        </div>
        <motion.ul
          className="principle-directory grid gap-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
        >
          {solutions.map(([title,text],index)=>(
            <motion.li
              key={title}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
              className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
            >
              <span>{String(index+1).padStart(2,"0")}</span>
              <strong>{title}</strong>
              <p>{text}</p>
            </motion.li>
          ))}
        </motion.ul>
      </div>
    </motion.div>
  </section>
  <section className="section surface-section">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="compact-heading-row">
          <div>
            <div className="eyebrow">One operating model</div>
            <h2>From requested result to verified delivery.</h2>
          </div>
        </div>
        <motion.div
          className="flow-grid grid gap-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delayChildren: 0.1, staggerChildren: 0.2 }}
        >
          {operatingModel.map(([n,t,x], index)=>(
            <motion.div
              key={n}
              initial={{ x: -10, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
              className="flow-card border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
            >
              <span>{n}</span>
              <h3>{t}</h3>
              <p>{x}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.div>
  </section>
  <section className="section compact-section">
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell callout">
        <div>
          <div className="eyebrow">Choose the right view</div>
          <h2>Individual and enterprise use share the platform, but not the same product story.</h2>
        </div>
        <div className="actions flex items-center justify-center gap-4 mt-6">
          <motion.a
            key="individuals-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/individuals"
          >
            For individuals
          </motion.a>
          <motion.a
            key="enterprise-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/enterprise"
          >
            For enterprises
          </motion.a>
          <motion.a
            key="trust-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.2 } }}
            className="text-link inline-flex items-center gap-2 text-white font-medium hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/trust"
          >
            Trust boundary →
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>}
