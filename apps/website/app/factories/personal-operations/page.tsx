import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Personal Operations Factory",
  description: "ILAIOS Personal Operations Factory is a bounded review-only foundation for deterministic personal-operation plans such as checklist, reminder, note, calendar and email drafts.",
  alternates: { canonical: "/factories/personal-operations", languages: { en: "/factories/personal-operations", tr: "/tr/factories/personal-operations", "x-default": "/factories/personal-operations" } },
};

const stages = [
  ["01", "Define a bounded objective", "Create a named plan with explicit non-empty steps rather than allowing an open-ended personal automation request."],
  ["02", "Use draft-only actions", "The current implementation allows calendar, checklist, email, note and reminder drafts only."],
  ["03", "Hash payloads", "Each step retains a SHA-256 digest of its payload so the review projection can preserve deterministic evidence without silently changing content."],
  ["04", "Fail closed on unsafe actions", "Unsupported actions, duplicate step IDs, missing plans and invalid state transitions stop instead of broadening authority."],
  ["05", "Approve for review", "A plan must receive an explicit approver before its review projection becomes available."],
  ["06", "No external account mutation", "The current foundation explicitly forbids applying the plan to external personal systems or accounts."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Personal Operations Factory</div><h1>Personal automation plans that remain reviewable before they touch anything external.</h1><p className="lead">Personal Operations Factory is a bounded implemented foundation for deterministic review-only plans. It supports a small set of draft actions, hashes step payloads, requires explicit review approval and forbids direct mutation of external personal systems.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-first personal operations</div><h2>Automation intent does not automatically become account authority.</h2></div><p className="muted">The current implementation does not send emails, create calendar events, modify reminders or write to external accounts. It prepares bounded draft plans for review.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Explicit human boundary</div><h2>Draft, evidence and approval stay visible before any future external execution path.</h2></div><div className="actions"><Link className="button" href="/factories">All factories</Link><Link className="button secondary" href="/individuals">For individuals</Link></div></div></section>
</>; }
