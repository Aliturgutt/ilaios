import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Official ILAIOS contact information for general company and product enquiries.",
  alternates: { canonical: "/contact", languages: { en: "/contact", tr: "/tr/contact", "x-default": "/contact" } },
};

export default function Contact(){return <>
  <section className="shell page-hero"><div className="eyebrow">Contact</div><h1>Official ILAIOS contact channels.</h1><p className="lead">For general company, product, and early collaboration enquiries, use the verified public contact address below. Dedicated partnership and security channels will be published only after they are separately verified for external use.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Official channels</div><h2>Verified contact.</h2><div className="grid"><article className="card"><h3>General contact</h3><p>Company, product, and general enquiries.</p><p><a href="mailto:contact@ilaios.com">contact@ilaios.com</a></p><span className="status-chip">Public channel active</span></article><article className="card"><h3>Partnerships</h3><p>Technology, ecosystem, distribution, and strategic collaboration enquiries.</p><span className="status-chip">Dedicated channel pending verification</span></article><article className="card"><h3>Security</h3><p>Responsible disclosure and security-related communication.</p><span className="status-chip">Dedicated channel pending verification</span></article></div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Security note</div><h2>Operational addresses stay private.</h2></div><div><p className="muted">Infrastructure-specific mailboxes are intentionally not presented as general public contact channels. A dedicated security-reporting address will appear here when it is verified.</p></div></div></section>
</>}
