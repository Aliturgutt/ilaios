import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Official ILAIOS contact-channel status and verification information.",
  alternates: { canonical: "/contact", languages: { en: "/contact", tr: "/tr/contact", "x-default": "/contact" } },
};

export default function Contact(){return <>
  <section className="shell page-hero"><div className="eyebrow">Contact</div><h1>Official ILAIOS contact channels.</h1><p className="lead">ILAIOS is in active development. Public business, partnership, product, and security channels are published only after the corresponding corporate mailbox is verified for external use.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Official channels</div><h2>Verification before publication.</h2><div className="grid"><article className="card"><h3>Business</h3><p>General company and early product discussions.</p><span className="status-chip">Public channel being verified</span></article><article className="card"><h3>Partnerships</h3><p>Technology, ecosystem, distribution, and strategic collaboration enquiries.</p><span className="status-chip">Public channel being verified</span></article><article className="card"><h3>Security</h3><p>Responsible disclosure and security-related communication.</p><span className="status-chip">Dedicated channel being verified</span></article></div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Security note</div><h2>Operational addresses stay private.</h2></div><div><p className="muted">Infrastructure-specific mailboxes are intentionally not presented as general public contact channels. A dedicated security-reporting address will appear here when it is verified.</p></div></div></section>
</>}
