import Image from "next/image";
import Link from "next/link";

const pillars = [
  ["Governed", "Critical actions are constrained by explicit policies, permissions, approvals, and observable control paths."],
  ["Verifiable", "Execution is designed around evidence, validation, auditability, and deterministic behavior where possible."],
  ["Composable", "Clients, services, agents, and workflows are separated by durable contracts instead of fragile presentation-layer coupling."],
] as const;

export default function Home() {
  return (
    <>
      <section className="shell hero">
        <div className="hero-copy">
          <div className="eyebrow">Intelligent systems. Governed execution.</div>
          <h1>Build autonomy you can control.</h1>
          <p className="lead">ILAIOS is developing infrastructure for intelligent automation with explicit control boundaries, verifiable execution, and security-first operations.</p>
          <div className="actions">
            <Link className="button" href="/platform">Explore the platform</Link>
            <Link className="button secondary" href="/about">Why ILAIOS</Link>
          </div>
          <div className="hero-meta" aria-label="Development status">
            <span className="status-dot" /> Active development
            <span className="meta-separator">•</span>
            Architecture-led
            <span className="meta-separator">•</span>
            Evidence-first
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <Image src="/brand/website-hero.jpg" alt="" width={1920} height={1080} priority />
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="eyebrow">Design principles</div>
          <h2>Autonomy without surrendering control.</h2>
          <div className="grid">
            {pillars.map(([title, text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell split-copy">
          <div>
            <div className="eyebrow">System direction</div>
            <h2>Control plane first. Interfaces second.</h2>
          </div>
          <div>
            <p className="lead small">ILAIOS is designed so authoritative decisions remain in governed backend services while desktop, mobile, and web clients act as projections of that authority.</p>
            <div className="actions"><Link className="text-link" href="/platform">Read the platform direction →</Link></div>
          </div>
        </div>
      </section>

      <section className="section compact-section">
        <div className="shell callout">
          <div><div className="eyebrow">Development status</div><h2>Building in public, without overstating what is ready.</h2></div>
          <div><p className="muted">This site distinguishes engineering direction from released capability. Planned features are not presented as commercially available until they are actually validated and released.</p></div>
        </div>
      </section>
    </>
  );
}
