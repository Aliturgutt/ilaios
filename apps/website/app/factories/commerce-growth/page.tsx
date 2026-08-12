import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Commerce & Growth Factory",
  description: "ILAIOS Commerce & Growth Factory is a bounded review-only foundation for evidence-backed growth proposals with trusted sources, approved draft channels and zero paid-spend authority.",
  alternates: { canonical: "/factories/commerce-growth", languages: { en: "/factories/commerce-growth", tr: "/tr/factories/commerce-growth", "x-default": "/factories/commerce-growth" } },
};

const stages = [
  ["01", "Register trusted evidence", "Store explicit source locators and SHA-256 digests; untrusted or unknown evidence cannot support a proposal."],
  ["02", "Define objective and audience", "A plan records its objective, audience and bounded channels instead of implying broad marketing authority."],
  ["03", "Use allowed draft channels", "The implemented foundation allows content drafts, email drafts, social drafts and sales-enablement proposals only."],
  ["04", "Block paid spend", "Any non-zero paid-spend request fails closed; billing, ad buying and budget mutation are outside this bounded factory."],
  ["05", "Approve for review", "A deterministic plan digest is retained and the proposal must be explicitly approved before a review projection is available."],
  ["06", "No publishing mutation", "External commerce or growth mutation is explicitly forbidden by the current implementation."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Commerce & Growth Factory</div><h1>Evidence-backed growth proposals without hidden spend or publishing authority.</h1><p className="lead">Commerce & Growth Factory is a bounded implemented foundation. It creates deterministic review-only growth plans from trusted evidence, limits channels to supported draft and sales-enablement outputs, requires approval for review and rejects paid spend or external mutation.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-only growth workflow</div><h2>Planning is separated from spending, publishing and account mutation.</h2></div><p className="muted">This foundation does not claim ad-network execution, automatic outreach, billing authority or autonomous campaign publishing.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Bounded by design</div><h2>Trusted evidence and explicit review gates come before any external action.</h2></div><div className="actions"><Link className="button" href="/factories">All factories</Link><Link className="button secondary" href="/security">Security model</Link></div></div></section>
</>; }
