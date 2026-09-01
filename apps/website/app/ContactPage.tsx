type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Official ILAIOS contact channel.",
    lead: "Use the verified public mailbox below. Choose a topic to prefill the subject; every route goes to the same verified address.",
    primary: "contact@ilaios.com",
    topics: [["General & product", "Company, product and partnership enquiries", "ILAIOS — General & product"], ["Support & privacy", "User support, privacy and personal-data requests", "ILAIOS — Support & privacy"], ["Security & abuse", "Responsible vulnerability, misuse, spam and fraud reports", "ILAIOS — Security & abuse"]],
    note: "Dedicated functional aliases are published only after their exact public purpose is verified.",
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS resmi iletişim kanalı.",
    lead: "Aşağıdaki doğrulanmış kamu adresini kullanın. Konu seçimi e-posta başlığını hazırlar; tüm yollar aynı doğrulanmış adrese gider.",
    primary: "contact@ilaios.com",
    topics: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "ILAIOS — Genel ve ürün"], ["Destek ve gizlilik", "Kullanıcı desteği, gizlilik ve kişisel veri talepleri", "ILAIOS — Destek ve gizlilik"], ["Güvenlik ve kötüye kullanım", "Sorumlu güvenlik açığı, kötüye kullanım, spam ve dolandırıcılık bildirimleri", "ILAIOS — Güvenlik ve kötüye kullanım"]],
    note: "Özel işlevsel adresler yalnız kamuya açık amaçları doğrulandıktan sonra yayınlanır.",
  },
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <>
    <section className="shell contact-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><div><p className="lead">{c.lead}</p><p><a className="button" href={`mailto:${c.primary}`}>{c.primary}</a></p></div></section>
    <section className="section compact-section"><div className="shell contact-directory" data-visual-role="contact-directory">{c.topics.map(([title, description, subject], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{description}</p></div><a href={`mailto:${c.primary}?subject=${encodeURIComponent(subject)}`}>{locale === "tr" ? "E-posta oluştur" : "Compose email"}</a></article>)}</div></section>
    <section className="section compact-section surface-section"><div className="shell status-note"><span>{locale === "tr" ? "Doğrulanmış kamu kanalı" : "Verified public route"}</span><p>{c.note}</p></div></section>
  </>;
}
