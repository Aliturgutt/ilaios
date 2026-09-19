import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "ILAIOS Core", description: "Understand the ILAIOS Core control, validation, evidence and recovery model.", alternates: { canonical: "/core", languages: { en: "/core", tr: "/tr/core", "x-default": "/core" } } };

const flow = [
  ["01", "Goal & context", "The requested result enters with the identity, project context and limits that define the operating boundary."],
  ["02", "Control", "Policy, permissions and approvals decide what the work is allowed to do before sensitive execution."],
  ["03", "Plan & execute", "The work is decomposed and routed to bounded capabilities; a model or agent name is never authority by itself."],
  ["04", "Verify & deliver", "Acceptance checks, evidence and bounded recovery decide whether the result is ready to deliver."],
] as const;

export default function Page(){ return <>
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS Core</div>
    <h1 className="text-5xl font-semibold tracking-tighter mb-6">One control authority around every governed execution.</h1>
    <p className="text-xl leading-relaxed mb-8">Core connects the requested outcome to permissions, bounded execution, verification, evidence and recovery without handing system authority to a model, agent or provider.</p>
    <div className="actions flex items-center gap-4">
      <Link className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200" href="/capabilities">Explore capabilities</Link>
      <Link className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200" href="/architecture">See the architecture</Link>
    </div>
  </section>
  <section className="section pt-20 pb-20">
    <div className="shell">
      <div className="compact-heading-row">
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">Controlled path</div>
          <h2 className="text-3xl font-semibold tracking-tighter mb-4">From intent to an accepted result.</h2>
        </div>
      </div>
      <div className="audience-process grid gap-6 pt-8">
        {flow.map(([n,title,text])=>
          <article key={n} className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200">
            <span className="text-xs font-bold text-gray-400">{n}</span>
            <strong className="text-lg font-semibold">{title}</strong>
            <p className="text-base leading-relaxed">{text}</p>
          </article>
        )}
      </div>
    </div>
  </section>
  <section className="section surface-section pt-20 pb-20 bg-gray-800">
    <div className="shell audience-focus">
      <div>
        <span className="micro-label text-xs font-semibold tracking-wider text-gray-400">Core principle</span>
        <h2 className="text-3xl font-semibold tracking-tighter mb-4 text-white">Execution resources can change. Authority does not.</h2>
      </div>
      <div className="audience-outcome-list grid gap-6 pt-8">
        <article>
          <span className="text-xs font-semibold text-gray-400">01</span>
          <div>
            <strong className="text-lg font-semibold text-white">Single control boundary</strong>
            <p className="text-base leading-relaxed text-gray-300">Identity, policy, approvals and permitted actions remain explicit and centralized.</p>
          </div>
        </article>
        <article>
          <span className="text-xs font-semibold text-gray-400">02</span>
          <div>
            <strong className="text-lg font-semibold text-white">Bounded execution</strong>
            <p className="text-base leading-relaxed text-gray-300">Agents, skills, tools and providers operate only inside the scope granted to the job.</p>
          </div>
        </article>
        <article>
          <span className="text-xs font-semibold text-gray-400">03</span>
          <div>
            <strong className="text-lg font-semibold text-white">Independent acceptance</strong>
            <p className="text-base leading-relaxed text-gray-300">Validation and required approvals determine whether produced work can advance.</p>
          </div>
        </article>
        <article>
          <span className="text-xs font-semibold text-gray-400">04</span>
          <div>
            <strong className="text-lg font-semibold text-white">Evidence and recovery</strong>
            <p className="text-base leading-relaxed text-gray-300">Material state, provenance and failure handling stay reviewable when work succeeds or fails.</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</>; }