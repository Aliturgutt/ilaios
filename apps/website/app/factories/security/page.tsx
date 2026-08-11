import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Security Factory",
  description: "ILAIOS Security Factory is a bounded defensive workflow for authorized code, secret, supply-chain, infrastructure and local/test web security analysis with remediation, retest and independent verification.",
  alternates: { canonical: "/factories/security", languages: { en: "/factories/security", tr: "/tr/factories/security", "x-default": "/factories/security" } },
};

const stages = [
  ["01", "Authorize scope", "Accept only an explicitly authorized repository or configured localhost/test target. Scope is not inferred or widened by the security role."],
  ["02", "Static analysis", "Run bounded defensive checks for source risk, secrets, dependency/supply-chain concerns and infrastructure configuration."],
  ["03", "Web/API observation", "Validate supplied HTTP observations only for configured local/test targets; arbitrary external network scanning is outside this factory boundary."],
  ["04", "Classify findings", "Keep finding type, severity context, affected target and evidence reviewable instead of reducing security to a model-generated verdict."],
  ["05", "Remediate inside authority", "Propose or execute only the bounded remediation allowed by the active workflow and permission model."],
  ["06", "Retest", "Repeat the applicable deterministic checks after remediation and keep the before/after evidence linked."],
  ["07", "Verify independently", "Security verification remains separate from the role that produced or remediated the finding."],
  ["08", "Stop or deliver", "Fail closed on missing authorization or unresolved gates; deliver reviewable findings and evidence when acceptance criteria pass."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Security Factory</div><h1>Bounded defensive security analysis with authorization, evidence and verifier separation.</h1><p className="lead">Security Factory is a verified bounded defensive factory in the ILAIOS repository. It combines authorized code, secret, supply-chain, infrastructure and local/test web-security checks with remediation, retest and independent verification boundaries.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Defensive boundary</div><h2>Security capability does not mean unrestricted scanning authority.</h2></div><p className="muted">The current verified factory is deliberately fail-closed. It does not exploit arbitrary systems, authorize external penetration testing, or imply SOC 2, ISO 27001 or other external certification.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Security governance</div><h2>Permissions, DLP, evidence and independent verification remain part of the same control chain.</h2></div><div className="actions"><Link className="button" href="/security">Security model</Link><Link className="button secondary" href="/security/permissions">Permission boundaries</Link><Link className="text-link" href="/agents">Agent organization →</Link></div></div></section>
</>; }
