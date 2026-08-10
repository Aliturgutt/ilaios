export const metadata = { title: "Security" };

const principles = [
  ["Least privilege", "Permissions are intended to be explicit, narrow, revocable, and scoped to the action being performed."],
  ["Human authority", "Operations that require human approval remain gated by human authority instead of being silently delegated."],
  ["Fail-closed behavior", "Sensitive paths are designed to stop when authority, validation, or required evidence is missing."],
  ["Evidence over assertion", "Security-relevant outcomes should be supported by verifiable records rather than model confidence alone."],
  ["Separated authority", "User interfaces do not become the source of truth for security or runtime policy decisions."],
  ["No premature claims", "ILAIOS does not claim certifications, compliance status, or external attestations that have not been formally obtained."],
] as const;

export default function Security() {
  return (
    <>
      <section className="shell page-hero">
        <div className="eyebrow">Security</div>
        <h1>Security is part of execution, not a layer added later.</h1>
        <p className="lead">ILAIOS is being engineered around constrained authority, validation gates, explicit approvals, auditable actions, and fail-closed behavior for sensitive operations.</p>
      </section>
      <section className="section">
        <div className="shell">
          <div className="eyebrow">Engineering principles</div>
          <h2>Control boundaries are designed into the system.</h2>
          <div className="grid two-up">
            {principles.map(([title, text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}
          </div>
        </div>
      </section>
      <section className="section">
        <div className="shell split-copy">
          <div><div className="eyebrow">Reporting</div><h2>Responsible security reporting.</h2></div>
          <div><p className="lead small">A dedicated public security-reporting mailbox will be published after the corresponding corporate mailbox is verified. Until then, no unverified contact address is represented here as operational.</p></div>
        </div>
      </section>
    </>
  );
}
