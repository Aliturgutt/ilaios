import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "İletişim",
  description: "ILAIOS resmi iletişim bilgileri.",
  alternates: { canonical: "/tr/contact", languages: { tr: "/tr/contact", en: "/contact", "x-default": "/contact" } },
};

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">İletişim</div><h1>ILAIOS ile iletişime geçin.</h1><p className="lead">ILAIOS aktif geliştirme aşamasındadır. İş, ortaklık, ürün ve güvenlik kanalları yalnızca ilgili kurumsal mailbox dış kullanıma doğrulandıktan sonra yayınlanır.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Resmi kanallar</div><h2>Yayınlamadan önce doğrulama.</h2><div className="grid"><article className="card"><h3>İş ve ürün</h3><p>Genel şirket iletişimi ve erken ürün görüşmeleri.</p><span className="status-chip">Genel kanal doğrulanıyor</span></article><article className="card"><h3>Ortaklıklar</h3><p>Teknoloji, ekosistem, dağıtım ve stratejik iş birliği görüşmeleri.</p><span className="status-chip">Ortaklık kanalı doğrulanıyor</span></article><article className="card"><h3>Güvenlik</h3><p>Sorumlu güvenlik bildirimi ve güvenlikle ilgili iletişim.</p><span className="status-chip">Özel kanal doğrulanıyor</span></article></div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Güvenlik notu</div><h2>Operasyon adresleri özel kalır.</h2></div><div><p className="muted">Altyapıya özel mailbox'lar genel iletişim adresi olarak yayınlanmaz. Doğrulanmış güvenlik bildirim adresi hazır olduğunda burada yer alacaktır.</p></div></div></section>
</>}
