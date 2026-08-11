import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Web Factory",
  description: "ILAIOS Web Factory'nin gereksinim ve bilgi mimarisinden responsive geliştirme, validation, security, SEO, performans ve deployment hazırlığına uzanan kontrollü web üretim akışı.",
  alternates: { canonical: "/tr/factories/web", languages: { en: "/factories/web", tr: "/tr/factories/web", "x-default": "/factories/web" } },
};

const stages = [
  ["01", "Hedef & gereksinimler", "Hedef kitleyi, iş amacını, içerik sınırlarını, fonksiyonel ihtiyaçları, kısıtları ve kabul kriterlerini tanımla."],
  ["02", "Bilgi mimarisi", "Gereksinimleri navigasyon, sayfa hiyerarşisi, kullanıcı yolculukları, içerik yapısı ve responsive davranışa dönüştür."],
  ["03", "İçerik & tasarım sistemi", "Müşteri, sertifika veya ürün erişilebilirliği uydurmadan doğru ürün/şirket içeriği ve tutarlı görsel sistem hazırla."],
  ["04", "Geliştirme", "Semantic, responsive ve erişilebilir sayfaları sürdürülebilir web bileşenleriyle uygula."],
  ["05", "Kalite & güvenlik", "Link, form, browser davranışı, erişilebilirlik, görsel tutarlılık, güvenlik sınırları, privacy/legal yüzeyleri ve gerekli spam/abuse kontrollerini doğrula."],
  ["06", "SEO & performans", "Metadata, heading, canonical/hreflang, sitemap/robots, internal links, görsel teslimi ve performans duyarlı uygulamayı doğrula."],
  ["07", "Deployment hazırlığı", "Domain/DNS/TLS, build, deployment, rollback, monitoring, gerektiğinde analytics/consent ve production smoke testini hazırla."],
  ["08", "Evidence & bakım", "Validation sonuçlarını, versioned artifact'ları, deployment evidence'ını, rollback bağlamını ve uygun güncelleme stratejisini koru."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Web Factory</div><h1>Tek seferlik üretim değil, kontrollü website yaşam döngüsü.</h1><p className="lead">Web Factory, bir iş hedefini gereksinim, bilgi mimarisi, içerik, geliştirme, doğrulama, deployment hazırlığı ve evidence adımlarından oluşan yapılandırılmış web üretim akışına dönüştürmek için tasarlanan ILAIOS yeteneğidir.</p></section>
  <section className="section"><div className="shell"><p className="muted">Capability maturity ile release state ayrı izlenir. Bu sayfa kanonik workflow'u açıklar; tüm Web Factory fonksiyonlarının bugün genel kullanıma açık olduğunu iddia etmez.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Ortak ILAIOS kontrolleri</div><h2>Authorization, validation, evidence ve recovery workflow'un parçası olarak kalır.</h2></div><div className="actions"><Link className="button" href="/tr/how-it-works">ILAIOS nasıl çalışır</Link><Link className="button secondary" href="/tr/capabilities">Tüm yetenekler</Link></div></div></section>
</>; }
