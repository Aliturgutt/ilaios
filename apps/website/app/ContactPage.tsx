type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Contact ILAIOS.",
    lead: "Use the email address that matches your request.",
    topics: [["General & product", "Company, product and partnership enquiries", "contact@ilaios.com"], ["Support", "User and product support", "support@ilaios.com"], ["Privacy", "Privacy and personal-data requests", "privacy@ilaios.com"], ["Security", "Responsible vulnerability reports", "security@ilaios.com"], ["Abuse", "Spam, fraud and misuse reports", "abuse@ilaios.com"]],
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS ile iletişim.",
    lead: "Talebinize uygun e-posta adresini kullanın.",
    topics: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "contact@ilaios.com"], ["Destek", "Kullanıcı ve ürün desteği", "support@ilaios.com"], ["Gizlilik", "Gizlilik ve kişisel veri talepleri", "privacy@ilaios.com"], ["Güvenlik", "Sorumlu güvenlik açığı bildirimleri", "security@ilaios.com"], ["Kötüye kullanım", "Spam, dolandırıcılık ve kötüye kullanım bildirimleri", "abuse@ilaios.com"]],
  },
} as const;

const heroStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 0.9fr) minmax(300px, 1.1fr)",
  alignItems: "center",
  gap: "28px",
  paddingTop: "26px",
  paddingBottom: "22px",
} as const;

const titleStyle = {
  maxWidth: "520px",
  marginTop: "8px",
  marginBottom: 0,
  fontSize: "clamp(1.65rem, 2.45vw, 2.2rem)",
  lineHeight: 1.06,
  letterSpacing: "-0.035em",
} as const;

const leadWrapStyle = {
  justifySelf: "end",
  width: "min(100%, 500px)",
} as const;

const leadStyle = {
  margin: 0,
  maxWidth: "42ch",
  fontSize: "clamp(.95rem, 1.05vw, 1.08rem)",
  lineHeight: 1.48,
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro" style={heroStyle}>
      <div><div className="eyebrow">{c.eyebrow}</div><h1 style={titleStyle}>{c.title}</h1></div>
      <div style={leadWrapStyle}><p className="lead" style={leadStyle}>{c.lead}</p></div>
    </section>
    <section className="section compact-section" style={{paddingTop: "16px", paddingBottom: "24px"}}><div className="shell contact-directory" data-visual-role="contact-directory">{c.topics.map(([title, description, email], index) => <article key={title}><span>{String(index + 1).padStart(2,"0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${email}`}>{email}</a></article>)}</div></section>
  </>;
}
