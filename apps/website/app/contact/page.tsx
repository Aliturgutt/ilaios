import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Official ILAIOS contact information for company, product, support, privacy, security, and abuse reporting enquiries.",
  alternates: { canonical: "/contact", languages: { en: "/contact", tr: "/tr/contact", "x-default": "/contact" } },
};

const channels = [
  ["General contact", "Company, product, and general enquiries.", "contact@ilaios.com"],
  ["Information", "General company and product information requests.", "info@ilaios.com"],
  ["Support", "Product and user support requests.", "support@ilaios.com"],
  ["Security", "Responsible security and vulnerability reporting.", "security@ilaios.com"],
  ["Privacy", "Privacy and personal-data related requests.", "privacy@ilaios.com"],
  ["Abuse reporting", "Reports of misuse, spam, fraud, or other abuse involving ILAIOS services.", "abuse@ilaios.com"],
] as const;

export default function Contact(){return <>
  <section className="shell page-hero"><div className="eyebrow">Contact</div><h1>Official ILAIOS contact channels.</h1><p className="lead">Use the channel that matches your request. These addresses are verified public ILAIOS routes; infrastructure and administrative mailboxes remain private.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Official channels</div><h2>Reach the right team.</h2><div className="grid contact-channel-grid">{channels.map(([title,description,email]) => <article className="card contact-channel" key={email}><h3>{title}</h3><p>{description}</p><p><a className="text-link" href={`mailto:${email}`}>{email}</a></p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Security note</div><h2>Operational addresses stay private.</h2></div><div><p className="muted">AWS root, operations, cloud, billing, postmaster, catch-all, and other infrastructure-specific routes are intentionally not published as customer contact channels.</p></div></div></section>
</>}
