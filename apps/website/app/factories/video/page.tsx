import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Video & Media Factory",
  description: "How ILAIOS Video & Media Factory structures research, script, scene and shot planning, assets, governed execution, rendering, validation, publishing preparation, evidence, recovery, and cost control.",
  alternates: { canonical: "/factories/video", languages: { en: "/factories/video", tr: "/tr/factories/video", "x-default": "/factories/video" } },
};

const stages = [
  ["01", "Topic & research", "Start from a defined content goal, gather relevant research, and preserve source context where the workflow depends on factual claims."],
  ["02", "Content & script planning", "Turn the brief into a structured content plan, script, continuity constraints, and acceptance requirements."],
  ["03", "Scene & shot planning", "Break the script into scenes and shots with duration, composition, continuity, asset, and generation requirements."],
  ["04", "Asset & execution planning", "Plan uploaded/generated assets, rights/provenance, quality/cost thresholds and eligible execution resources inside policy."],
  ["05", "Media, voice & audio", "Acquire or generate visual media, voice, audio, and captions through bounded job steps."],
  ["06", "Assembly & rendering", "Compose the media artifact, render through the admitted technical profile, and retain artifact identity."],
  ["07", "Technical & content validation", "Check media properties, continuity/content requirements, policy and rights constraints, and required acceptance criteria before approval."],
  ["08", "Approval & platform adaptation", "Where required, obtain approval and prepare platform-specific format, metadata, cover/thumbnail, disclosure, and scheduling data."],
  ["09", "Publish & verify", "Publishing is a side effect: use idempotency, rate-limit handling, delivery verification, duplicate prevention, and post-publish checks."],
  ["10", "Evidence, metrics & recovery", "Retain provenance, validation, delivery state, cost, retry/recovery context, and metrics without treating provider-reported success as final proof."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Video / Media Factory</div><h1>A media lifecycle that remains controlled from references to delivery.</h1><p className="lead">Video / Media Factory coordinates the content-production chain while keeping validation, evidence, recovery, publishing side effects, and cost controls explicit.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Preview</span><p>Repository evidence includes a real finished-product Video E2E path with independent acceptance. Live zero-cost external provider availability is still not verified and must fail closed when no eligible route exists.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Video / Media Factory at a glance</div><h2>Turn references into a reviewable, verified media target.</h2></div><p>The visual describes the target production path. A “verified video” label means required acceptance checks must pass for that exact artifact; it is not a promise that every external generation route is currently available.</p></div><ThemedDiagram light="/visuals/video-light.avif" dark="/visuals/video-dark.avif" alt="ILAIOS Video and Media Factory diagram showing request, reference analysis, production, verification and delivery" caption="Target workflow: request → analyze references → produce → verify → deliver. External generation and publishing remain separately evidence-gated." priority /></div></section>

  <section className="section"><div className="shell"><p className="muted">This page describes the canonical workflow plus the current bounded repository truth. It does not claim that every external provider, publishing destination, or media format is generally available today.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Provider-independent by design</div><h2>Execution resources can change without becoming the source of workflow authority.</h2><p className="muted">The public product experience does not require users to choose a provider. Eligibility, policy, cost and quality remain governed behind the product boundary.</p></div><div className="actions"><Link className="button" href="/use-ilaios">How to use ILAIOS</Link><Link className="button secondary" href="/platform/evidence">Evidence model</Link></div></div></section>
</>; }
