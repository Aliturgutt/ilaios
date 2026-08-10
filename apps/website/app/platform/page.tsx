export const metadata = { title: "Platform" };

const capabilities = [
  ["Governed execution", "Critical actions are designed to flow through explicit permissions, approvals, policy checks, and bounded authority."],
  ["Evidence-first operations", "Meaningful execution paths are designed to produce validation evidence, audit context, and durable operational records."],
  ["Deterministic by default", "When a deterministic path exists, ILAIOS is designed to prefer it over unnecessary model-driven decision making."],
  ["Bounded intelligence", "AI and agent capabilities are treated as tools inside controlled workflows rather than unrestricted system authority."],
  ["Control-plane authority", "Authoritative runtime decisions remain in backend and control-plane services instead of being delegated to presentation clients."],
  ["Composable clients", "Desktop, mobile, and web interfaces can evolve independently while relying on stable contracts and shared backend authority."],
] as const;

export default function Platform() {
  return (
    <>
      <section className="shell page-hero">
        <div className="eyebrow">Platform</div>
        <h1>Infrastructure for governed intelligent operations.</h1>
        <p className="lead">ILAIOS is being developed as a control-oriented platform for coordinating workflows, software capabilities, and AI-assisted execution without moving authority into individual agents or interfaces.</p>
      </section>
      <section className="section">
        <div className="shell">
          <div className="eyebrow">Architecture direction</div>
          <h2>Designed around authority, evidence, and durable contracts.</h2>
          <div className="grid two-up">
            {capabilities.map(([title, text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}
          </div>
        </div>
      </section>
      <section className="section">
        <div className="shell split-copy">
          <div><div className="eyebrow">Current stage</div><h2>Built incrementally, validated continuously.</h2></div>
          <div><p className="lead small">ILAIOS remains under active development. Public descriptions on this site communicate engineering direction and validated design principles; they do not imply that every planned capability is commercially available today.</p></div>
        </div>
      </section>
    </>
  );
}
