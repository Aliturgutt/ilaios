import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Official ILAIOS contact information for general enquiries, information requests, product support, security reporting, privacy, and abuse reporting.",
  alternates: { canonical: "/contact", languages: { en: "/contact", tr: "/tr/contact", "x-default": "/contact" } },
};

const channels = [
  ["General contact", "Company, product, and general enquiries.", "contact@ilaios.com"],
  ["Information", "General company and product information requests.", "info@ilaios.com"],
  ["Support", "Product and user support requests.", "support@ilaios.com"],
  ["Security", "Responsible disclosure and security-related reports.", "security@ilaios.com"],
  ["Privacy", "Privacy-related requests and questions.", "privacy@ilaios.com"],
  ["Abuse reporting", "Reports of misuse, spam, fraud, or other abuse involving ILAIOS services or infrastructure.", "abuse@ilaios.com"],
] as const;

export default function Contact(){return <>
  <section className="shell page-hero"><div className="eyebrow">Contact</div><h1>Official ILAIOS contact channels.</h1><p className="lead">Use the channel that best matches your request. The addresses below are verified public routes for ILAIOS; operational and infrastructure administration mailboxes remain private.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Official channels</div><h2>Reach the right destination.</h2><div className="grid two-up">{channels.map(([title,text,email])=><article className="card" key={email}><h3>{title}</h3><p>{text}</p><p><a className="text-link" href={`mailto:${email}`}>{email}</a></p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Operational boundary</div><h2>Administrative mailboxes stay private.</h2></div><div><p className="muted">Infrastructure, billing, cloud operations, root-account, postmaster, and catch-all routes are not presented as general public contact channels.</p></div></div></section>
</>}
