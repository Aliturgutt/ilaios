export const metadata = { title: "Contact" };

export default function Contact() {
  return (
    <>
      <section className="shell page-hero">
        <div className="eyebrow">Contact</div>
        <h1>Start a conversation with ILAIOS.</h1>
        <p className="lead">ILAIOS is currently in active development. Business, partnership, product, and security contact channels will be published here as each corporate mailbox is verified.</p>
      </section>
      <section className="section">
        <div className="shell grid">
          <article className="card"><h3>Business</h3><p>General company and early product discussions.</p><span className="status-chip">Corporate mailbox pending verification</span></article>
          <article className="card"><h3>Partnerships</h3><p>Technology, distribution, ecosystem, and strategic collaboration enquiries.</p><span className="status-chip">Corporate mailbox pending verification</span></article>
          <article className="card"><h3>Security</h3><p>Responsible disclosure and security-related communication.</p><span className="status-chip">Dedicated channel pending verification</span></article>
        </div>
      </section>
    </>
  );
}
