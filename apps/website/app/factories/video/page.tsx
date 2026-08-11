import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Video & Media Factory",
  description: "How ILAIOS Video & Media Factory structures research, script, scene and shot planning, assets, provider routing, audio, rendering, validation, publishing preparation, evidence, recovery, and cost control.",
  alternates: { canonical: "/factories/video", languages: { en: "/factories/video", tr: "/tr/factories/video", "x-default": "/factories/video" } },
};

const stages = [
  ["01", "Topic & research", "Start from a defined content goal, gather relevant research, and preserve source context where the workflow depends on factual claims."],
  ["02", "Content & script planning", "Turn the brief into a structured content plan, script, continuity constraints, and acceptance requirements."],
  ["03", "Scene & shot planning", "Break the script into scenes and shots with duration, composition, continuity, asset, and generation requirements."],
  ["04", "Asset & provider planning", "Plan uploaded/generated assets, rights/provenance, provider selection, cost/quality thresholds, and fallback paths."],
  ["05", "Media, voice & audio", "Acquire or generate visual media, voice, audio, and captions through replaceable providers and bounded job steps."],
  ["06", "Assembly & rendering", "Compose the episode or media artifact, render through the selected technical profile, and retain artifact identity."],
  ["07", "Technical & content validation", "Check media properties, continuity/content requirements, policy and rights constraints, and required acceptance criteria before approval."],
  ["08", "Approval & platform adaptation", "Where required, obtain approval and prepare platform-specific format, metadata, cover/thumbnail, disclosure, and scheduling data."],
  ["09", "Publish & verify", "Publishing is a side effect: use idempotency, rate-limit handling, delivery verification, duplicate prevention, and post-publish checks."],
  ["10", "Evidence, metrics & recovery", "Retain provenance, validation, delivery state, cost, retry/recovery context, and metrics without treating provider-reported success as final proof."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Video / Media Factory</div><h1>A media lifecycle that remains controlled from research to delivery.</h1><p className="lead">Video / Media Factory is the ILAIOS capability direction for coordinating the full content-production chain while keeping provider choice, validation, evidence, recovery, publishing side effects, and cost controls explicit.</p></section>
  <section className="section"><div className="shell"><p className="muted">This page describes the canonical workflow and verified architectural direction. It does not claim that every provider, publishing destination, or factory function is generally available today.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Provider-independent by design</div><h2>Generation providers can change without becoming the source of workflow authority.</h2></div><div className="actions"><Link className="button" href="/how-it-works">How ILAIOS works</Link><Link className="button secondary" href="/platform/evidence">Evidence model</Link></div></div></section>
</>; }
