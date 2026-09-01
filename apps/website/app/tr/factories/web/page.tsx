import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../../../CanonicalSystemDetail";
import ThemedDiagram from "../../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Web Factory",
  description: "ILAIOS Web Factory; hedeften araştırma, bilgi mimarisi, görsel tasarım, implementation, browser/security/accessibility/performance/SEO/visual QA, bounded repair, deployment validation ve finished-site evidence zincirine ilerler.",
  alternates: { canonical: "/tr/factories/web", languages: { tr: "/tr/factories/web", en: "/factories/web", "x-default": "/factories/web" } },
};

const stages = [
  ["01", "Hedef & araştırma", "Hedef kitleyi, iş amacını, güvenilir girdileri, kısıtları, kabul kriterlerini ve araştırma ihtiyacını tanımla."],
  ["02", "Bilgi mimarisi & metin", "Uydurma iddia, müşteri veya availability üretmeden navigasyon, sayfa hiyerarşisi, kullanıcı yolculukları ve doğru içeriği oluştur."],
  ["03", "Design system & görsel yön", "Tipografi, spacing, surfaces, kompozisyon, görsel, etkileşim ve responsive stratejiyi proje bağlamından türet."],
  ["04", "Implementation", "Semantic responsive sayfaları ve etkileşimleri erişilebilir, bakım yapılabilir web primitives ile oluştur."],
  ["05", "Browser & functional QA", "Route, link, form, browser davranışı, etkileşim ve responsive kompozisyonu kontrol et."],
  ["06", "Security & accessibility QA", "İlgili güvenlik sınırlarını, privacy/legal yüzeyleri, klavye davranışı, contrast, focus ve erişilebilir içeriği doğrula."],
  ["07", "Performance & SEO", "Metadata, headings, canonical/hreflang, sitemap/robots, internal links, images ve performans-duyarlı implementation'ı doğrula."],
  ["08", "Visual QA & anti-generic review", "Hierarchy, density, composition, brand coherence, repetition, mobile transformation ve generic-AI design sinyallerini değerlendir."],
  ["09", "Acceptance & bounded repair", "Gerekli gate'ler kabulü belirler. Başarısız kontroller self-reported success yerine bounded repair ve yeniden doğrulama üretir."],
  ["10", "Deployment validation & evidence", "Deployment istenmiş ve yetkilendirilmişse deployed artifact'i doğrula; version, validation ve rollback bağlamını koru."],
] as const;

const motionGroups = [
  ["Sürükleyici sahneler", "3D hero bölümleri, scroll ile hareket eden 3D sahneler, parallax ve camera transition'ları, particle effect'leri, WebGL arka planları ve 3D typography."],
  ["Etkileşimli ürünler", "Ürün/model döndürme ile pointer, mouse ve touch etkileşimleri sayesinde incelenebilir ürün deneyimleri."],
  ["Güvenli teslim", "Düşük kapasiteli cihazlar için responsive 2D fallback, açık performance budget, accessibility kontrolleri ve reduced-motion fallback."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Web Factory</div><h1>Hedef sonuç mockup veya kısmi generation değil, doğrulanmış bitmiş web sitesidir.</h1><p className="lead">Web Factory; iş hedefini bağlama göre tasarım, implementation, bağımsız quality gate'leri, bounded repair ve evidence içeren tam web sitesi yaşam döngüsüne dönüştüren kanonik ILAIOS workflow'udur.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Önizleme</span><p>Repository-bounded Web production ve governed Vercel delivery boundary evidence-backed durumdadır. Güncel exact master'ın canonical public domainde üretim kanıtı ayrı bir production proof olarak kalır.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Web Factory özeti</div><h2>Yeni web sitesi oluştur. Mevcut siteyi yükselt. Desktop-style web ürünleri üret.</h2></div><p>Bu diyagram public ürün anlatımıdır. “Production-ready” hedef artifact'i tanımlar; güncel public deployment durumu ayrıca evidence-gated kalır.</p></div><ThemedDiagram light="/visuals/web-light.avif" dark="/visuals/web-dark.avif" alt="ILAIOS Web Factory diyagramı: web sitesi, upgrade ve web app için request, analyze, build or upgrade, verify ve deliver" caption="Hedef workflow: request → analyze → build or upgrade → verify → deliver. Public release için exact deployment evidence gerekir." priority /></div></section>

  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Ürün gerçeği</div><h2>Kanonik hedef ile güncel release state ayrı kalır.</h2></div><div><p className="lead small">Finished-product hedefi deploy edilebilir site artifact'lerini, gerekli QA'yı ve evidence'i kapsar. Bu kanonik workflow'un varlığı her aşamanın bugün genel public hizmet olarak hazır olduğunu iddia etmez.</p><p className="muted">Güncel capability maturity repository implementation, tests, CI, runtime ve deployment evidence ile belirlenir.</p></div></div></section>

  <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Planlanan capability pack</div><h2>3D / Motion Web, aynı yönetilen Web Factory içinde.</h2><div className="factory-status-row"><span className="availability-chip is-development">Planlandı</span><small>Implementation, browser/device performance, accessibility ve release evidence geçmeden genel production-readiness iddiası yoktur.</small></div></div><p>Zengin motion ayrı bir web motoru değil, isteğe bağlı Web Factory yeteneği olmalıdır. Aynı policy, validation, evidence ve release sınırları otoriter kalır.</p></div><div className="grid">{motionGroups.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><div className="callout"><div><div className="eyebrow">Önce progressive enhancement</div><h2>Cihaz destekliyorsa sürükleyici. Desteklemiyorsa yine kullanılabilir.</h2><p className="muted">Acceptance contract; graceful 2D fallback, mobile/touch davranışı, performance budget, keyboard/content accessibility ve <code>prefers-reduced-motion</code> davranışını 3D/Motion sonucu kabul edilmeden önce zorunlu tutmalıdır.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Kanonik üretim sırası</div><h2>Tasarım ve kabul birinci sınıf aşamalardır.</h2></div><p className="muted">Workflow araştırma, görsel yön, browser QA, visual QA, acceptance, bounded repair ve deployment validation içerir.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Tam yaşam döngüsü</div><h2>Kanonik zincir tüm quality gate'leri görünür yapar.</h2></div><p>Website Goal → Research → Information Architecture → Copy → Design System → Visual Design → Implementation → Browser QA → Security QA → Accessibility → Performance → SEO → Visual QA → Acceptance → bounded repair → Deployment Validation → Finished Website + Evidence.</p></div><CanonicalSystemDetail locale="tr" variant="web" /></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Native design intelligence</div><h2>Dynamic; rastgele değil, bağlamdan türetilmiş demektir.</h2><p className="muted">Marka, hedef kitle, içerik, trust gereksinimleri, bilgi yoğunluğu ve cihaz öncelikleri design strategy'yi şekillendirir; structured quality evidence otoriter kalır.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></section>
</>; }
