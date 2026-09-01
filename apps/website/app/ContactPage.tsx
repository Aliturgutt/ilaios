type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Official ILAIOS contact channel.",
    lead: "Use the verified public mailbox below for company, product, support, privacy, security, abuse or other public enquiries. Dedicated functional aliases are published only after their exact public purpose is verified.",
    channels: [["General & product", "Company, product and partnership enquiries", "contact@ilaios.com"], ["Support & privacy", "User support, privacy and personal-data requests", "contact@ilaios.com"], ["Security & abuse", "Responsible vulnerability, misuse, spam and fraud reports", "contact@ilaios.com"]],
    noteLabel: "Verified public route",
    note: "contact@ilaios.com is the public ILAIOS mailbox verified for website use. Infrastructure, billing, administrative and unverified functional aliases are intentionally not published as customer contact channels.",
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS resmi iletişim kanalı.",
    lead: "Şirket, ürün, destek, gizlilik, güvenlik, kötüye kullanım veya diğer kamuya açık talepler için aşağıdaki doğrulanmış adresi kullanın. İşlevsel özel adresler yalnız kamuya açık amaçları doğrulandıktan sonra yayınlanır.",
    channels: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "contact@ilaios.com"], ["Destek ve gizlilik", "Kullanıcı desteği, gizlilik ve kişisel veri talepleri", "contact@ilaios.com"], ["Güvenlik ve kötüye kullanım", "Sorumlu güvenlik açığı, kötüye kullanım, spam ve dolandırıcılık bildirimleri", "contact@ilaios.com"]],
    noteLabel: "Doğrulanmış kamu kanalı",
    note: "contact@ilaios.com, web sitesinde kullanım için doğrulanmış kamuya açık ILAIOS adresidir. Altyapı, faturalandırma, yönetim ve doğrulanmamış işlevsel adresler müşteri iletişim kanalı olarak yayınlanmaz.",
  },
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell contact-directory" data-visual-role="contact-directory">{c.channels.map(([title, description, email], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${email}`}>{email}</a></article>)}</div></section>
    <section className="section compact-section surface-section"><div className="shell status-note"><span>{c.noteLabel}</span><p>{c.note}</p></div></section>
  </>;
}
