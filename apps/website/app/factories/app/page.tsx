import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";

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
  <section className="shell page-hero"><div className="eyebrow">ILAIOS App Factory</div><h1>From product idea to a bounded application outcome, with release authority kept explicit.</h1><p className="lead">App Factory is no longer only a review-plan concept: repository evidence includes a bounded Windows-first finished-product path. That does not make Android/iOS, production signing or Store publication complete.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Preview</span><p>Windows-first bounded finished-product evidence exists in the repository. Android/iOS, signing, Store publication, live install and arbitrary-app breadth remain separate gates.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">App Factory target lifecycle</div><h2>Turn product ideas into store-ready targets without claiming Store publication before proof.</h2></div><p>The supplied visual describes the target product lifecycle. “Store Ready” is a release-readiness target, not evidence that signing, submission, certification or live installation has already occurred.</p></div><ThemedDiagram light="/visuals/app-light.avif" dark="/visuals/app-dark.avif" alt="ILAIOS App Factory diagram showing prompt and references, product and UX specification, architecture, build, test and verify, iOS or Android preparation and Store Ready target" caption="Target lifecycle: prompt + references → product/UX spec → architecture → build → test & verify → platform packaging → Store readiness. Current mobile/Store completion remains evidence-gated." priority /></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Current reality + target truth</div><h2>Windows evidence is current reality. Mobile Store release remains target work.</h2></div><p className="muted">This separation prevents the target architecture from being presented as production completion.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Release boundary</div><h2>Build evidence does not silently grant signing, Store submission or publication authority.</h2><p className="muted">Those actions require their own credentials, approvals, exact artifact identity, platform checks and external evidence.</p></div><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/factories">All factories</Link></div></div></section>
</>; }
