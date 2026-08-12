import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "İletişim",
  description: "ILAIOS genel iletişim, bilgi talepleri, ürün desteği, güvenlik bildirimi, gizlilik ve kötüye kullanım bildirimleri için resmi iletişim adresleri.",
  alternates: { canonical: "/tr/contact", languages: { tr: "/tr/contact", en: "/contact", "x-default": "/contact" } },
};

const channels = [
  ["Genel iletişim", "Şirket, ürün ve genel iletişim talepleri.", "contact@ilaios.com"],
  ["Bilgi", "Şirket ve ürün hakkında genel bilgi talepleri.", "info@ilaios.com"],
  ["Destek", "Ürün ve kullanıcı destek talepleri.", "support@ilaios.com"],
  ["Güvenlik", "Sorumlu güvenlik bildirimi ve güvenlikle ilgili raporlar.", "security@ilaios.com"],
  ["Gizlilik", "Gizlilikle ilgili talepler ve sorular.", "privacy@ilaios.com"],
  ["Kötüye kullanım bildirimi", "ILAIOS hizmetleri veya altyapısıyla ilişkili spam, dolandırıcılık, kötüye kullanım ve benzeri raporlar.", "abuse@ilaios.com"],
] as const;

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">İletişim</div><h1>ILAIOS resmi iletişim kanalları.</h1><p className="lead">Talebinize en uygun kanalı kullanın. Aşağıdaki adresler ILAIOS için doğrulanmış kamuya açık yönlendirmelerdir; operasyon ve altyapı yönetim adresleri özel kalır.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Resmi kanallar</div><h2>Doğru kanala ulaşın.</h2><div className="grid two-up">{channels.map(([title,text,email])=><article className="card" key={email}><h3>{title}</h3><p>{text}</p><p><a className="text-link" href={`mailto:${email}`}>{email}</a></p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Operasyon sınırı</div><h2>Yönetim adresleri özel kalır.</h2></div><div><p className="muted">Altyapı, faturalama, cloud operasyonları, root hesap, postmaster ve catch-all adresleri genel iletişim kanalı olarak yayınlanmaz.</p></div></div></section>
</>}
