import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "App Factory",
  description: "ILAIOS App Factory is a bounded review-only foundation for deterministic Windows, Android and iOS client change, build and test plans without direct client mutation, deployment, signing or store submission authority.",
  alternates: { canonical: "/factories/app", languages: { en: "/factories/app", tr: "/tr/factories/app", "x-default": "/factories/app" } },
};

const stages = [
  ["01", "Choose a supported client platform", "The current bounded foundation accepts Windows, Android and iOS planning requests only."],
  ["02", "Create a bounded request", "Supported actions are review-oriented client change, build and test plans with an explicit objective and artifact target."],
  ["03", "Keep client roots protected", "Requests that target desktop, mobile or website implementation roots fail closed instead of mutating client source directly."],
  ["04", "Hash the request deterministically", "Equivalent requests produce the same SHA-256 request digest so the review projection has stable evidence."],
  ["05", "Require approval for review", "Only explicitly approved requests can produce a review projection."],
  ["06", "Block release authority", "Direct client mutation, deployment, signing and app-store submission are explicitly outside this foundation."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS App Factory</div><h1>App planning with deterministic evidence and a hard boundary before client mutation or release.</h1><p className="lead">App Factory is a bounded implemented foundation in the ILAIOS platform. It prepares deterministic review-only requests for supported client platforms while keeping implementation roots, deployment, signing and store submission outside its authority.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-only app workflow</div><h2>Planning remains separate from implementation and distribution authority.</h2></div><p className="muted">Repository tests explicitly verify deterministic requests, approval gating, protected client roots and fail-closed deployment/signing/store boundaries.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Bounded by design</div><h2>App Factory prepares governed review artifacts; it does not silently become a release pipeline.</h2></div><div className="actions"><Link className="button" href="/factories">All factories</Link><Link className="button secondary" href="/desktop">Desktop</Link></div></div></section>
</>; }
