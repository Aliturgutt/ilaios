import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Hakkımızda",
  description: "ILAIOS'un kontrollü akıllı otomasyon altyapısını neden geliştirdiğini öğrenin.",
  alternates: { canonical: "/tr/about", languages: { tr: "/tr/about", en: "/about", "x-default": "/about" } },
};

const principles = [
  ["Kolaylıktan önce kontrol", "Bir model işlem yapabiliyor diye otomasyon yetki sınırlarını aşmamalıdır. Önemli operasyonlar politika, izinler ve açık yürütme koşullarıyla sınırlandırılır."],
  ["Güvenden önce kanıt", "Sistem yalnızca başarılı olduğunu söylememeli; ne olduğunu, neyin doğrulandığını ve sonucun neden kabul edildiğini gösterebilmelidir."],
  ["Arayüzden önce mimari", "Masaüstü, mobil ve web istemcileri backend otoritesinin görünümüdür; böylece arayüzler değişirken sistem sınırları korunabilir."],
] as const;

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">Hakkımızda</div><h1>Net yetkiyle faydalı otomasyon.</h1><p className="lead">ILAIOS, kontrollü akıllı otomasyon sistemleri geliştiren bağımsız bir teknoloji şirketidir. Hedefimiz her ne pahasına olursa olsun otonomi değil; açık kontrol, kanıt ve operasyonel görünürlük ile güvenilir yürütmedir.</p></section>
  <section className="section"><div className="shell"><div className="eyebrow">Çalışma ilkeleri</div><h2>Güven bir mühendislik özelliğidir.</h2><div className="grid">{principles.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
  <section className="section architecture-section"><div className="shell split-copy"><div><div className="eyebrow">Ne geliştiriyoruz?</div><h2>Akıllı işler için bir kontrol sistemi.</h2></div><div><p className="lead small">Ürün yönü; yönetilen iş akışlarını, sınırlandırılmış araçları, akıllı yetenekleri, onay kapılarını, doğrulamayı ve kanıtı tek bir operasyon modelinde birleştirir.</p><p className="muted">ILAIOS aktif geliştirme aşamasındadır. Bu site, doğrulanmış mühendislik yönünü henüz yayınlanmamış özelliklerden açıkça ayırır.</p><div className="actions"><Link className="text-link" href="/tr/platform">Platformu inceleyin →</Link><Link className="text-link" href="/tr/security">Güvenlik yaklaşımı →</Link></div></div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Şirket yönü</div><h2>Uzun ömürlü operasyonel güven için.</h2></div><div><p className="muted">Hedef mimari; modeller, araçlar, arayüzler ve sağlayıcılar değişse bile yetki, doğrulama, kanıt ve yürütme sözleşmelerini kalıcı tutar.</p></div></div></section>
</>}
