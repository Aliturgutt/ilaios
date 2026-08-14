type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Official ILAIOS contact channels.",
    lead: "Choose the route that matches your request. Public contact addresses are separated from private infrastructure and administrative mailboxes.",
    channels: [["General", "Company and product enquiries", "contact@ilaios.com"], ["Information", "Company and product information", "info@ilaios.com"], ["Support", "Product and user support", "support@ilaios.com"], ["Security", "Responsible vulnerability reporting", "security@ilaios.com"], ["Privacy", "Privacy and personal-data requests", "privacy@ilaios.com"], ["Abuse", "Misuse, spam and fraud reports", "abuse@ilaios.com"]],
    noteLabel: "Security note",
    note: "AWS root, operations, cloud, billing, postmaster, catch-all and other infrastructure-specific routes are intentionally not published as customer contact channels.",
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS resmi iletişim kanalları.",
    lead: "Talebinize uygun kanalı seçin. Kamuya açık iletişim adresleri, özel altyapı ve yönetim adreslerinden ayrı tutulur.",
    channels: [["Genel", "Şirket ve ürün talepleri", "contact@ilaios.com"], ["Bilgi", "Şirket ve ürün bilgisi", "info@ilaios.com"], ["Destek", "Ürün ve kullanıcı desteği", "support@ilaios.com"], ["Güvenlik", "Sorumlu güvenlik açığı bildirimi", "security@ilaios.com"], ["Gizlilik", "Gizlilik ve kişisel veri talepleri", "privacy@ilaios.com"], ["Kötüye kullanım", "Kötüye kullanım, spam ve dolandırıcılık bildirimleri", "abuse@ilaios.com"]],
    noteLabel: "Güvenlik notu",
    note: "AWS root, operations, cloud, billing, postmaster, catch-all ve diğer altyapıya özel adresler müşteri iletişim kanalı olarak yayınlanmaz.",
  },
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell contact-directory" data-visual-role="contact-directory">{c.channels.map(([title, description, email], index) => <article key={email}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${email}`}>{email}</a></article>)}</div></section>
    <section className="section compact-section surface-section"><div className="shell status-note"><span>{c.noteLabel}</span><p>{c.note}</p></div></section>
  </>;
}
