import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "İletişim",
  description: "ILAIOS genel şirket ve ürün iletişimi için resmi iletişim bilgileri.",
  alternates: { canonical: "/tr/contact", languages: { tr: "/tr/contact", en: "/contact", "x-default": "/contact" } },
};

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">İletişim</div><h1>ILAIOS resmi iletişim kanalları.</h1><p className="lead">Genel şirket, ürün ve erken iş birliği görüşmeleri için aşağıdaki doğrulanmış genel iletişim adresini kullanabilirsiniz. Özel ortaklık ve güvenlik kanalları, dış kullanıma ayrıca doğrulandıktan sonra yayınlanacaktır.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Resmi kanallar</div><h2>Doğrulanmış iletişim.</h2><div className="grid"><article className="card"><h3>Genel iletişim</h3><p>Şirket, ürün ve genel iletişim talepleri.</p><p><a href="mailto:contact@ilaios.com">contact@ilaios.com</a></p><span className="status-chip">Genel kanal aktif</span></article><article className="card"><h3>Ortaklıklar</h3><p>Teknoloji, ekosistem, dağıtım ve stratejik iş birliği görüşmeleri.</p><span className="status-chip">Özel kanal doğrulaması bekleniyor</span></article><article className="card"><h3>Güvenlik</h3><p>Sorumlu güvenlik bildirimi ve güvenlikle ilgili iletişim.</p><span className="status-chip">Özel kanal doğrulaması bekleniyor</span></article></div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Güvenlik notu</div><h2>Operasyon adresleri özel kalır.</h2></div><div><p className="muted">Altyapıya özel mailbox'lar genel iletişim adresi olarak yayınlanmaz. Doğrulanmış güvenlik bildirim adresi hazır olduğunda burada yer alacaktır.</p></div></div></section>
</>}
