import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Kontrollü Akıllı Sistemler",
  description: "ILAIOS; açık yetki sınırları, doğrulanabilir yürütme ve güvenlik odaklı operasyonlar için akıllı otomasyon altyapısı geliştirir.",
  alternates: { canonical: "/tr", languages: { tr: "/tr", en: "/", "x-default": "/" } },
};

const pillars = [
  ["Yönetilebilir", "Kritik işlemler açık politikalar, izinler, onaylar ve gözlemlenebilir kontrol yollarıyla sınırlandırılır."],
  ["Doğrulanabilir", "Yürütme; kanıt, doğrulama, denetlenebilirlik ve mümkün olan yerde deterministik davranış etrafında tasarlanır."],
  ["Birleştirilebilir", "İstemciler, servisler, ajanlar ve iş akışları sunum katmanına bağımlı olmak yerine kalıcı sözleşmelerle ayrılır."],
] as const;

const flow = [
  ["01", "Niyet", "Bir hedef istemci veya onaylanmış bir arayüz üzerinden sisteme girer."],
  ["02", "Politika", "Yetki, izinler ve yürütme sınırları değerlendirilir."],
  ["03", "Yürütme", "Deterministik araçlar ve sınırlandırılmış akıllı yetenekler işi gerçekleştirir."],
  ["04", "Doğrulama", "Testler, doğrulayıcılar ve kanıt sonucun kabul edilebilir olup olmadığını belirler."],
  ["05", "Teslim", "Doğrulanmış çıktılar gözlemlenebilir bir iz ile kullanıcıya sunulur."],
] as const;

export default function Page() {
  return <>
    <section className="shell hero"><div className="hero-copy"><div className="eyebrow">Akıllı sistemler. Kontrollü yürütme.</div><h1>Kontrol edebileceğiniz otonomi.</h1><p className="lead">ILAIOS; açık kontrol sınırları, doğrulanabilir yürütme ve güvenlik odaklı operasyonlarla akıllı otomasyon altyapısı geliştiriyor.</p><div className="actions"><Link className="button" href="/tr/platform">Platformu inceleyin</Link><Link className="button secondary" href="/tr/about">ILAIOS neden var?</Link></div><div className="hero-meta" aria-label="Geliştirme durumu"><span className="status-dot" /> Aktif geliştirme <span className="meta-separator">•</span> Mimari odaklı <span className="meta-separator">•</span> Kanıt odaklı</div></div><div className="hero-visual" aria-hidden="true"><Image src="/brand/website-hero.jpg" alt="" width={1920} height={1080} priority sizes="(max-width: 900px) calc(100vw - 40px), 48vw" quality={82} /></div></section>
    <section className="section"><div className="shell"><div className="eyebrow">Tasarım ilkeleri</div><h2>Kontrolden vazgeçmeden otonomi.</h2><div className="grid">{pillars.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Kontrol mimarisi</div><h2>Niyetten kanıta uzanan yönetilen bir yol.</h2></div><p className="lead small">Kullanıcı arayüzü sistem otoritesi değildir. ILAIOS; politika değerlendiren, yürütmeyi koordine eden, sonuçları doğrulayan ve kanıtı koruyan bir kontrol katmanı etrafında tasarlanır.</p></div><div className="control-stack"><div className="stack-layer"><span>İSTEMCİ KATMANI</span><strong>Masaüstü · Mobil · Web</strong><small>Hedefler, onaylar, gözlemlenebilirlik ve teslim</small></div><div className="stack-connector">↓ yönetilen istekler / gözlemlenebilir sonuçlar ↑</div><div className="stack-layer authority-layer"><span>YETKİLİ KONTROL KATMANI</span><strong>Politika · Orkestrasyon · İzinler · Doğrulama</strong><small>Karar yetkisi sunum istemcilerinin dışında kalır</small></div><div className="stack-connector">↓ sınırlandırılmış yürütme / kanıt ↑</div><div className="stack-layer"><span>YÜRÜTME KATMANI</span><strong>Araçlar · Servisler · Ajanlar · İş Akışları</strong><small>Önce deterministik yollar; uygun olduğunda akıllı yetenekler</small></div></div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Yürütme yaşam döngüsü</div><h2>İş, gizemli değil incelenebilir olmalı.</h2></div><p className="lead small">Hedef işletim modeli, kullanıcıların ne olduğunu ve neden olduğunu anlayabilmesi için anlamlı durum geçişlerini açık hale getirir.</p></div><div className="flow-grid">{flow.map(([number,title,text]) => <article className="flow-card" key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section evidence-section"><div className="shell evidence-grid"><div><div className="eyebrow">Kanıt ve güvenlik</div><h2>Güven, kontrol ve kanıttan gelmeli.</h2><p className="lead small">ILAIOS; hassas işlemlerin yalnızca bir ajanın başarı iddiasına değil, izinlere, onay kapılarına, doğrulamaya ve denetlenebilir kanıta dayanabilmesi için geliştiriliyor.</p><div className="actions"><Link className="text-link" href="/tr/security">Güvenlik yaklaşımını inceleyin →</Link></div></div><div className="evidence-panel" aria-label="Örnek doğrulama zinciri"><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Politika kontrolü</strong><small>Yetki yürütmeden önce değerlendirilir</small></div></div><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Doğrulama kapısı</strong><small>Sonuç açık kriterlere göre kontrol edilir</small></div></div><div className="evidence-row"><span className="evidence-icon">✓</span><div><strong>Kanıt izi</strong><small>Anlamlı yürütme olayları gözlemlenebilir kalır</small></div></div></div></div></section>
    <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Geliştirme durumu</div><h2>Hazır olmayanı hazırmış gibi göstermeden geliştiriyoruz.</h2></div><div><p className="muted">Bu site mühendislik yönü ile yayınlanmış yetenekleri birbirinden ayırır. Planlanan özellikler gerçekten doğrulanıp yayınlanmadan ticari olarak kullanılabilir biçimde sunulmaz.</p></div></div></section>
  </>;
}
