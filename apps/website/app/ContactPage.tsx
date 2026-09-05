type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Contact ILAIOS.",
    lead: "Use the email address that matches your request.",
    primary: "contact@ilaios.com",
    topics: [["General & product", "Company, product and partnership enquiries", "contact@ilaios.com"], ["Support", "User and product support", "support@ilaios.com"], ["Privacy", "Privacy and personal-data requests", "privacy@ilaios.com"], ["Security", "Responsible vulnerability reports", "security@ilaios.com"], ["Abuse", "Spam, fraud and misuse reports", "abuse@ilaios.com"]],
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS ile iletişim.",
    lead: "Talebinize uygun e-posta adresini kullanın.",
    primary: "contact@ilaios.com",
    topics: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "contact@ilaios.com"], ["Destek", "Kullanıcı ve ürün desteği", "support@ilaios.com"], ["Gizlilik", "Gizlilik ve kişisel veri talepleri", "privacy@ilaios.com"], ["Güvenlik", "Sorumlu güvenlik açığı bildirimleri", "security@ilaios.com"], ["Kötüye kullanım", "Spam, dolandırıcılık ve kötüye kullanım bildirimleri", "abuse@ilaios.com"]],
  },
} as const;

const heroStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 0.9fr) minmax(360px, 1.1fr)",
  alignItems: "center",
  gap: "48px",
  paddingTop: "44px",
  paddingBottom: "36px",
} as const;

const titleStyle = {
  maxWidth: "620px",
  marginTop: "12px",
  marginBottom: 0,
  fontSize: "clamp(2.35rem, 4vw, 3.7rem)",
  lineHeight: 1.02,
  letterSpacing: "-0.045em",
} as const;

const leadWrapStyle = {
  justifySelf: "end",
  width: "min(100%, 560px)",
} as const;

const leadStyle = {
  margin: 0,
  maxWidth: "44ch",
} as const;

const primaryStyle = {
  display: "inline-flex",
  marginTop: "18px",
  minHeight: "44px",
  alignItems: "center",
  justifyContent: "center",
  padding: "0 20px",
  border: "1px solid #808080",
  borderRadius: "8px",
  background: "transparent",
  color: "inherit",
  WebkitTextFillColor: "currentColor",
  textDecoration: "none",
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro" style={heroStyle}>
      <div><div className="eyebrow">{c.eyebrow}</div><h1 style={titleStyle}>{c.title}</h1></div>
      <div style={leadWrapStyle}><p className="lead" style={leadStyle}>{c.lead}</p><p><a className="button secondary" style={primaryStyle} href={`mailto:${c.primary}`}>{c.primary}</a></p></div>
    </section>
    <section className="section compact-section" style={{paddingTop: "24px", paddingBottom: "32px"}}><div className="shell contact-directory" data-visual-role="contact-directory">{c.topics.map(([title, description, email], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${email}`}>{email}</a></article>)}</div></section>
  </>;
}
