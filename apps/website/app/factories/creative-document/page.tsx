import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Creative & Document Factory",
  description: "ILAIOS Creative & Document Factory is a bounded implemented foundation for trusted-source document composition with deterministic provenance and approval-gated export.",
  alternates: { canonical: "/factories/creative-document", languages: { en: "/factories/creative-document", tr: "/tr/factories/creative-document", "x-default": "/factories/creative-document" } },
};

const stages = [
  ["01", "Register trusted sources", "Record explicit source IDs, locators and SHA-256 content digests; source trust is retained as part of the bounded input state."],
  ["02", "Compose deterministically", "Build a text artifact from non-blank sections and known trusted source IDs, producing a stable body digest."],
  ["03", "Fail closed on provenance", "Unknown, duplicate or untrusted source references stop composition instead of silently weakening evidence requirements."],
  ["04", "Require approval", "A composed artifact remains unapproved until an explicit approval transition occurs."],
  ["05", "Export a projection", "Only approved artifacts may export a projection containing title, body, body digest and source provenance."],
  ["06", "No external mutation", "The current foundation produces deterministic text artifacts and projections; it does not publish, send or mutate external systems."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Creative & Document Factory</div><h1>Document generation with trusted sources, deterministic provenance and an approval gate.</h1><p className="lead">Creative & Document Factory is a bounded implemented foundation in the ILAIOS repository. It composes text artifacts from explicitly registered trusted sources, hashes source and body content, blocks unsupported provenance and exports only after approval.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Bounded document workflow</div><h2>Drafting does not silently become publication authority.</h2></div><p className="muted">The current implementation is intentionally narrow. It does not claim arbitrary document-format generation, external publishing or autonomous distribution.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Governed output</div><h2>Approved projections preserve the source trail used to build the artifact.</h2></div><div className="actions"><Link className="button" href="/factories">All factories</Link><Link className="button secondary" href="/capabilities">Capabilities</Link></div></div></section>
</>; }
