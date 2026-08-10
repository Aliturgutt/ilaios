export const metadata = { title: "About" };

export default function About() {
  return (
    <>
      <section className="shell page-hero">
        <div className="eyebrow">About ILAIOS</div>
        <h1>Useful automation with clear authority.</h1>
        <p className="lead">ILAIOS is an independent technology company building systems for governed intelligent automation. The goal is not autonomy at any cost; it is reliable execution with explicit control, evidence, and operational visibility.</p>
      </section>
      <section className="section">
        <div className="shell grid">
          <article className="card"><h3>Control before convenience</h3><p>Automation should not bypass authority simply because a model can act. Important operations remain bounded by policy and permissions.</p></article>
          <article className="card"><h3>Evidence before confidence</h3><p>Systems should be able to show what happened, what was validated, and why an action was allowed.</p></article>
          <article className="card"><h3>Architecture before interface</h3><p>Clients are projections of backend authority, allowing desktop, mobile, and web experiences to evolve without weakening system boundaries.</p></article>
        </div>
      </section>
      <section className="section">
        <div className="shell split-copy">
          <div><div className="eyebrow">Development status</div><h2>Under active development.</h2></div>
          <div><p className="lead small">This website describes ILAIOS&apos;s current engineering direction. Planned capabilities are not represented as commercially available until they are actually released and validated.</p></div>
        </div>
      </section>
    </>
  );
}
