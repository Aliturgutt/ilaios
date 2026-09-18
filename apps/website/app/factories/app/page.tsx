import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";
import { motion } from "motion/react";

export const metadata: Metadata = {
  title: "App Factory",
  description: "ILAIOS App Factory is a Windows-first bounded finished-product path with deterministic build, test, package and evidence controls; Android/iOS, production signing and Store publication remain separate gates.",
  alternates: { canonical: "/factories/app", languages: { en: "/factories/app", tr: "/tr/factories/app", "x-default": "/factories/app" } },
};

const stages = [
  ["01", "Product goal & references", "Define the application outcome, users, platform target, constraints, references and acceptance criteria."],
  ["02", "Product & UX specification", "Turn the goal into bounded user flows, screen structure, interaction direction, data needs and reviewable requirements."],
  ["03", "Architecture & scope", "Resolve the minimum architecture, protected roots, permissions, data/auth boundaries and build/test plan before implementation."],
  ["04", "Governed implementation", "Implementation proceeds only inside admitted scope. Existing Core, policy, approval, tool and evidence authorities remain unchanged."],
  ["05", "Build, test & verify", "Run the required format/analyze/test/build/package checks and retain exact source-to-artifact evidence for the bounded platform path."],
  ["06", "Windows-first finished product", "The current repository evidence includes a bounded generated Flutter Windows application that was built, packaged and smoke-tested with content-addressed evidence."],
  ["07", "Mobile & Store gates", "Android/iOS execution, production signing, App Store/Play Store submission, certification and live install remain separate evidence-gated release work."],
] as const;

export default function Page() { return <>
  {/* Hero Section with Motion */}
  <section className="shell page-hero compact-page-hero pt-16 pb-16">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="eyebrow text-sm tracking-wider text-gray-400">ILAIOS App Factory</div>
      <h1 className="text-4xl font-bold tracking-tighter mb-4 text-white">From product idea to a bounded application outcome, with release authority kept explicit.</h1>
      <p className="text-base leading-relaxed mb-6 text-gray-300">App Factory is no longer only a review-plan concept: repository evidence includes a bounded Windows-first finished-product path. That does not make Android/iOS, production signing or Store publication complete.</p>
      <div className="factory-availability-banner flex items-center gap-3 mb-6">
        <span className="availability-chip is-preview px-2 py-1 text-xs font-medium bg-gray-800 text-white rounded">Preview</span>
        <p className="text-sm leading-none text-gray-300">Windows-first bounded finished-product evidence exists in the repository. Android/iOS, signing, Store publication, live install and arbitrary-app breadth remain separate gates.</p>
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">App Factory target lifecycle</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Turn product ideas into store-ready targets without claiming Store publication before proof.</h2>
        </div>
        <p className="text-base leading-relaxed text-gray-300">The supplied visual describes the target product lifecycle. “Store Ready” is a release-readiness target, not evidence that signing, submission, certification or live installation has already occurred.</p>
        <ThemedDiagram light="/visuals/app-light.avif" dark="/visuals/app-dark.avif" alt="ILAIOS App Factory diagram showing prompt and references, product and UX specification, architecture, build, test and verify, iOS or Android preparation and Store Ready target" caption="Target lifecycle: prompt + references → product/UX spec → architecture → build → test & verify → platform packaging → Store readiness. Current mobile/Store completion remains evidence-gated." priority />
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
          <div className="eyebrow text-sm tracking-wider text-gray-400">Current reality + target truth</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Windows evidence is current reality. Mobile Store release remains target work.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">This separation prevents the target architecture from being presented as production completion.</p>
        <div className="stage-list grid gap-6">
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
  <section className="section compact-section pt-20 pb-20">
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <div className="shell">
        <div className="compact-heading-row">
          <div className="eyebrow text-sm tracking-wider text-gray-400">Release boundary</div>
          <h2 className="text-3xl font-bold tracking-tighter mb-4 text-white">Build evidence does not silently grant signing, Store submission or publication authority.</h2>
        </div>
        <p className="text-base leading-relaxed mb-6 text-gray-300">Those actions require their own credentials, approvals, exact artifact identity, platform checks and external evidence.</p>
        <div className="actions flex items-center justify-center gap-4 mt-6">
          <motion.a
            key="use-ilaios-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0 } }}
            className="button bg-gray-900 text-white px-6 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            href="/use-ilaios"
          >
            How to use ILAIOS
          </motion.a>
          <motion.a
            key="all-factories-link"
            initial={{ x: -10, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
            className="button secondary border border-gray-600 px-6 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            href="/factories"
          >
            All factories
          </motion.a>
        </div>
      </div>
    </motion.div>
  </section>
</>; }