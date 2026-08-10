import Image from "next/image";
import Link from "next/link";

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
            <Link className="button secondary" href="/contact">Contact ILAIOS</Link>
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
            <article className="card"><h3>Governed</h3><p>Critical actions are constrained by explicit policies, permissions, approvals, and observable control paths.</p></article>
            <article className="card"><h3>Verifiable</h3><p>Execution is designed around evidence, validation, auditability, and deterministic behavior where possible.</p></article>
            <article className="card"><h3>Composable</h3><p>Clients, services, agents, and workflows are separated by durable contracts instead of fragile presentation-layer coupling.</p></article>
          </div>
        </div>
      </section>
    </>
  );
}
