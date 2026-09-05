type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Official ILAIOS contact channel.",
    lead: "Use the verified public mailbox that matches your request.",
    primary: "contact@ilaios.com",
    topics: [["General & product", "Company, product and partnership enquiries", "contact@ilaios.com"], ["Support", "User and product support", "support@ilaios.com"], ["Privacy", "Privacy and personal-data requests", "privacy@ilaios.com"], ["Security", "Responsible vulnerability reports", "security@ilaios.com"], ["Abuse", "Spam, fraud and misuse reports", "abuse@ilaios.com"]],
    note: "Each address is a verified public route for the purpose shown above.",
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS resmi iletişim kanalı.",
    lead: "Talebinize uygun doğrulanmış kamu adresini kullanın.",
    primary: "contact@ilaios.com",
    topics: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "contact@ilaios.com"], ["Destek", "Kullanıcı ve ürün desteği", "support@ilaios.com"], ["Gizlilik", "Gizlilik ve kişisel veri talepleri", "privacy@ilaios.com"], ["Güvenlik", "Sorumlu güvenlik açığı bildirimleri", "security@ilaios.com"], ["Kötüye kullanım", "Spam, dolandırıcılık ve kötüye kullanım bildirimleri", "abuse@ilaios.com"]],
    note: "Her adres yukarıda belirtilen amaç için doğrulanmış bir kamu kanalıdır.",
  },
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><div><p className="lead">{c.lead}</p><p><a className="button" href={`mailto:${c.primary}`}>{c.primary}</a></p></div></section>
    <section className="section compact-section"><div className="shell contact-directory" data-visual-role="contact-directory">{c.topics.map(([title, description, email], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${email}`}>{email}</a></article>)}</div></section>
    <section className="section compact-section surface-section"><div className="shell status-note"><span>{locale === "tr" ? "Doğrulanmış kamu kanalı" : "Verified public route"}</span><p>{c.note}</p></div></section>
  </>;
}
