import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "İletişim",
  description: "ILAIOS şirket, ürün, destek, gizlilik, güvenlik ve kötüye kullanım bildirimleri için resmi iletişim kanalları.",
  alternates: { canonical: "/tr/contact", languages: { tr: "/tr/contact", en: "/contact", "x-default": "/contact" } },
};

const channels = [
  ["Genel iletişim", "Şirket, ürün ve genel iletişim talepleri.", "contact@ilaios.com"],
  ["Bilgi", "Genel şirket ve ürün bilgisi talepleri.", "info@ilaios.com"],
  ["Destek", "Ürün ve kullanıcı destek talepleri.", "support@ilaios.com"],
  ["Güvenlik", "Sorumlu güvenlik ve güvenlik açığı bildirimleri.", "security@ilaios.com"],
  ["Gizlilik", "Gizlilik ve kişisel verilerle ilgili talepler.", "privacy@ilaios.com"],
  ["Kötüye kullanım bildirimi", "ILAIOS hizmetleriyle ilgili kötüye kullanım, spam, dolandırıcılık veya benzeri bildirimler.", "abuse@ilaios.com"],
] as const;

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">İletişim</div><h1>ILAIOS resmi iletişim kanalları.</h1><p className="lead">Talebinize uygun kanalı kullanın. Aşağıdaki adresler doğrulanmış genel ILAIOS yönlendirmeleridir; altyapı ve yönetim mailbox'ları özel tutulur.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Resmi kanallar</div><h2>Doğru kanala ulaşın.</h2><div className="grid contact-channel-grid">{channels.map(([title,description,email]) => <article className="card contact-channel" key={email}><h3>{title}</h3><p>{description}</p><p><a className="text-link" href={`mailto:${email}`}>{email}</a></p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Güvenlik notu</div><h2>Operasyon adresleri özel kalır.</h2></div><div><p className="muted">AWS root, operations, cloud, billing, postmaster, catch-all ve diğer altyapıya özel yönlendirmeler müşteri iletişim kanalı olarak yayınlanmaz.</p></div></div></section>
</>}
