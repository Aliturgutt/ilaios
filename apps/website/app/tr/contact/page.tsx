import type { Metadata } from "next";
import ContactPage from "../../ContactPage";
export const metadata: Metadata = { title: "İletişim", description: "Şirket, ürün, destek, gizlilik, güvenlik ve kötüye kullanım bildirimleri için resmi ILAIOS iletişim kanalları.", alternates: { canonical: "/tr/contact", languages: { tr: "/tr/contact", en: "/contact", "x-default": "/contact" } } };
export default function Page() { return <ContactPage locale="tr" />; }
