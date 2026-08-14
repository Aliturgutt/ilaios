import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Web Factory",
  description: "ILAIOS Web Factory: hedef ve araştırmadan bilgi mimarisi, görsel tasarım, geliştirme, QA, bounded repair, deployment validation ve finished-site evidence'a uzanan kanonik workflow.",
  alternates: { canonical: "/tr/factories/web", languages: { en: "/factories/web", tr: "/tr/factories/web", "x-default": "/factories/web" } },
};

const stages = [
  ["01", "Hedef & araştırma", "Hedef kitleyi, iş amacını, güvenilir girdileri, kısıtları, kabul kriterlerini ve araştırma ihtiyacını tanımla."],
  ["02", "Bilgi mimarisi & copy", "Navigasyon, sayfa hiyerarşisi, kullanıcı yolculukları ve doğru içeriği oluştur; iddia, müşteri veya erişilebilirlik uydurma."],
  ["03", "Design system & visual direction", "Typography, spacing, surface, composition, imagery, interaction ve responsive stratejiyi proje bağlamından türet."],
  ["04", "Implementation", "Semantic, responsive ve erişilebilir sayfaları sürdürülebilir web primitive'leriyle uygula."],
  ["05", "Browser & functional QA", "Route, link, form, browser davranışı, interaction ve responsive composition'ı kontrol et."],
  ["06", "Security & accessibility QA", "Uygulanabilir güvenlik sınırlarını, privacy/legal yüzeylerini, keyboard davranışını, contrast, focus ve erişilebilir içeriği doğrula."],
  ["07", "Performance & SEO", "Metadata, heading, canonical/hreflang, sitemap/robots, internal link, görsel teslimi ve performansı doğrula."],
  ["08", "Visual QA & anti-generic review", "Hiyerarşi, density, composition, marka tutarlılığı, repetition, mobil dönüşüm ve generic-AI tasarım sinyallerini değerlendir."],
  ["09", "Acceptance & bounded repair", "Gerekli gate'ler kabulü belirler; başarısız kontroller bounded repair ve yeniden validation üretir."],
  ["10", "Deployment validation & evidence", "Deployment istenmiş ve yetkilendirilmişse deployed artifact'ı doğrula; version, validation ve rollback bağlamını koru."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Web Factory</div><h1>Hedef çıktı mockup veya kısmi üretim değil, doğrulanmış bitmiş web sitesidir.</h1><p className="lead">Web Factory; iş hedefini context-derived design, implementation, bağımsız kalite gate'leri, bounded repair ve evidence içeren tam website yaşam döngüsüne dönüştüren kanonik ILAIOS workflow'udur.</p></section>
  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Ürün gerçeği</div><h2>Kanonik hedef ile mevcut release state ayrı kalır.</h2></div><div><p className="lead small">Finished-product hedefi deployable site artifact'ları ile gerekli QA ve evidence'ı birlikte kapsar. Bu kanonik workflow'un varlığı tüm aşamaların bugün genel kullanıma açık servis olduğu anlamına gelmez.</p><p className="muted">Mevcut maturity; repository implementation, tests, CI, runtime ve deployment evidence ile belirlenir.</p></div></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Kanonik üretim sırası</div><h2>Design ve acceptance birinci sınıf aşamalardır.</h2></div><p className="muted">Workflow; research, visual direction, browser QA, visual QA, acceptance, bounded repair ve deployment validation aşamalarını açıkça içerir.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Native design intelligence</div><h2>Dynamic, random demek değildir; template roulette değildir.</h2><p className="muted">Marka, audience, content, trust requirements, information density ve device priorities design strategy'yi şekillendirir; structured quality evidence otoriter kalır.</p></div><div className="actions"><Link className="button" href="/tr/how-it-works">ILAIOS nasıl çalışır?</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></section>
</>; }
