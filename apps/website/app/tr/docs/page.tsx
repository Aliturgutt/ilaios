import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Dokümanlar",
  description: "ILAIOS mimari, güvenlik, Core, yürütme, kanıt, API ve kurtarma dokümantasyonu için kamusal teknik merkez.",
  alternates: { canonical: "/tr/docs", languages: { en: "/docs", tr: "/tr/docs", "x-default": "/docs" } },
};

const docs = [
  ["Mimari", "Sistem sınırları, kontrol otoritesi ve istemci, yürütme ile kanıt arasındaki ilişki.", "/tr/architecture"],
  ["Güvenlik", "İzin sınırları, onay kapıları, minimum yetki yürütmesi ve fail-closed kontroller.", "/tr/security"],
  ["Core", "Tek kontrol otoritesi, sınırlandırılmış yürütme, doğrulama, kanıt ve kurtarma modeli.", "/tr/core"],
  ["Yürütme", "İstemciyi, modeli veya ajanı otoriteye dönüştürmeden kabul edilmiş işin kontrollü biçimde nasıl yürütüldüğü.", "/tr/platform/execution"],
  ["Kanıt", "Doğrulama, kaynak kökeni ve incelenebilir kayıtların önemli sonuçlara nasıl bağlı kaldığı.", "/tr/platform/evidence"],
  ["API", "Kamusal API referansları yalnız ilgili sözleşmeler kararlı ve doğrulanmış olduğunda burada yayınlanacaktır.", null],
  ["Kurtarma", "Kamusal kurtarma runbook'ları yalnız ilgili ürün yüzeyi için sürüme özel prosedürler doğrulandığında yayınlanacaktır.", null],
] as const;

const heroTitleStyle = {
  fontSize: "clamp(2.15rem, 3.5vw, 3.45rem)",
  lineHeight: 1.06,
  letterSpacing: "-0.04em",
  maxWidth: "19ch",
} as const;

export default function Page() {
  return <>
    <section className="shell page-hero compact-page-hero">
      <div className="eyebrow">Dokümanlar</div>
      <h1 style={heroTitleStyle}>Ürün sitesini teknik kılavuza çevirmeden derin teknik katmana ulaşın.</h1>
      <p className="lead">Bu merkezden kamusal teknik içeriğe doğrudan geçin. Ürün sayfaları sonucu anlatır; dokümantasyon bu sonucun arkasındaki kontrol, yürütme ve kanıt modelini açıklar.</p>
    </section>
    <section className="section">
      <div className="shell">
        <div className="detail-directory">
          {docs.map(([title, text, href]) => href ? (
            <Link href={href} key={title}><span>{title}</span><strong>{text}</strong><i>→</i></Link>
          ) : (
            <div className="status-note" key={title}><strong>{title}</strong><p>{text}</p></div>
          ))}
        </div>
      </div>
    </section>
  </>;
}
