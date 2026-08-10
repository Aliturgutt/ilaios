import Link from "next/link";

export const metadata = { title: "Security" };

const principles = [
  ["Least privilege", "Permissions are intended to be explicit, narrow, revocable, and scoped to the action being performed."],
  ["Human authority", "Operations that require human approval remain gated by human authority instead of being silently delegated."],
  ["Fail-closed behavior", "Sensitive paths are designed to stop when authority, validation, or required evidence is missing."],
  ["Evidence over assertion", "Security-relevant outcomes should be supported by verifiable records rather than model confidence alone."],
  ["Separated authority", "User interfaces do not become the source of truth for security or runtime policy decisions."],
  ["No premature claims", "ILAIOS does not claim certifications, compliance status, or external attestations that have not been formally obtained."],
] as const;

const details = [
  ["Permissions", "Least-privilege authority scoped by subject, action, resource, and runtime conditions.", "/security/permissions"],
  ["Approvals", "Explicit human authority for operations that must not be silently delegated.", "/security/approvals"],
  ["Audit", "Execution context and evidence that keep consequential actions inspectable.", "/security/audit"],
] as const;

const controls = [
  ["Request", "A sensitive action is requested through an authenticated interface."],
  ["Authorize", "Identity, scope, permissions, and required human authority are evaluated."],
  ["Constrain", "Allowed tools, targets, data boundaries, and execution conditions are limited."],
  ["Validate", "The resulting state is checked against explicit acceptance criteria."],
  ["Record", "Relevant evidence and audit context are retained for inspection."],
] as const;

export default function Security() {
  return (
    <>
      <section className="shell page-hero"><div className="eyebrow">Security</div><h1>Security is part of execution, not a layer added later.</h1><p className="lead">ILAIOS is being engineered around constrained authority, validation gates, explicit approvals, auditable actions, and fail-closed behavior for sensitive operations.</p></section>
      <section className="section"><div className="shell"><div className="eyebrow">Explore security controls</div><h2>Open the core trust boundaries.</h2><div className="detail-link-grid">{details.map(([title,text,href]) => <Link className="detail-link-card" href={href} key={href}><span>Security detail</span><h3>{title}</h3><p>{text}</p><strong>Open detail →</strong></Link>)}</div></div></section>
      <section className="section evidence-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Sensitive execution path</div><h2>Authority before side effects.</h2></div><p className="lead small">The intended security model requires meaningful actions to cross explicit control points rather than relying on a model or client to self-police.</p></div><div className="security-chain">{controls.map(([title,text],index) => <article key={title}><span>0{index+1}</span><div><h3>{title}</h3><p>{text}</p></div></article>)}</div></div></section>
      <section className="section"><div className="shell"><div className="eyebrow">Engineering principles</div><h2>Control boundaries are designed into the system.</h2><div className="grid two-up">{principles.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
      <section className="section"><div className="shell trust-boundary"><div><div className="eyebrow">Trust boundary</div><h2>Clients can request. The control plane decides.</h2><p className="lead small">Desktop, mobile, and web interfaces are designed to display state and request actions; they are not intended to become the authoritative source for permissions, policy, or security decisions.</p></div><div className="boundary-diagram"><div className="boundary-client"><span>CLIENTS</span><strong>Request · Approve · Observe</strong></div><div className="boundary-line"><span>validated contract</span></div><div className="boundary-core"><span>CONTROL PLANE</span><strong>Authorize · Constrain · Verify</strong></div></div></div></section>
      <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Reporting</div><h2>Responsible security reporting.</h2></div><div><p className="muted">A dedicated public security-reporting mailbox will be published after the corresponding corporate mailbox is verified. Until then, no unverified contact address is represented here as operational.</p></div></div></section>
    </>
  );
}
