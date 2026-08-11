import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Çözümler", description: "Yapay zekâ operasyonları, mühendislik, güvenlik, iş süreçleri ve araştırma için kontrollü akıllı otomasyon yaklaşımını inceleyin.", alternates: { canonical: "/tr/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Yapay zekâ operasyonları", "Model destekli işleri politika, onay, doğrulama ve kanıt sınırları içinde koordine eder; model çıktısını sistem otoritesi olarak kabul etmez.", ["Model ve araç izinlarını sınırla", "Hassas yan etkiler için onay iste", "Doğrulama ve kanıtı koru"]],
  ["Yazılım mühendisliği", "Mühendislik görevlerini araç izinleri, deterministik kontroller, inceleme kapıları ve izlenebilir yürütme sonuçlarıyla sınırlandırılmış işler olarak yapılandırır.", ["Planlamayı yürütme yetkisinden ayır", "Deterministik kalite kapıları çalıştır", "İncelenebilir yürütme bağlamını koru"]],
  ["Güvenlik operasyonları", "Hassas işlemlerin izinlere bağlı, incelenebilir ve denetlenebilir kaldığı kontrollü güvenlik iş akışlarını desteklemeyi hedefler.", ["Araçları ve hedefleri açıkça sınırla", "Yüksek etkili işlemleri eskale et", "Anlamlı güvenlik olaylarını kaydet"]],
  ["İş süreci otomasyonu", "Deterministik adımları akıllı yeteneklerle birleştirirken iş kurallarını ve yetkilendirmeyi modelin dışında tutar.", ["İş kısıtlarını prompt dışında tanımla", "Mümkün olduğunda deterministik adımlar kullan", "Teslimden önce tamamlanmayı doğrula"]],
  ["Araştırma ve bilgi çalışmaları", "Kaynak izlenebilirliği, doğrulama ve açık eskalasyon yollarıyla kanıt odaklı araştırma ve sentez akışlarını düzenler.", ["Kaynak kökenini görünür tut", "Bulgular ile kararları ayır", "Belirsizliği gizlemek yerine eskale et"]],
] as const;

const operatingModel = [
  ["1", "Yetkiyi tanımla", "İşi kimin isteyebileceğini, hangi araçların kullanılabileceğini ve hangi yan etkilerin onay gerektirdiğini belirle."],
  ["2", "Yürütmeyi sınırla", "İşi deterministik servisler veya açıkça sınırlandırılmış akıllı yetenekler üzerinden ilerlet."],
  ["3", "Sonucu doğrula", "Anlatısal başarı iddiasına güvenmek yerine sonucu kabul kriterlerine göre kontrol et."],
  ["4", "Kanıtı koru", "İnceleme, kurtarma ve hesap verebilir teslim için yeterli operasyonel bağlamı sakla."],
] as const;

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">Çözümler</div><h1>Operasyonel kontrol sınırları içindeki akıllı çalışma.</h1><p className="lead">ILAIOS, otomasyonun faydalı olurken hesap verebilir kalması gereken iş akışları için tasarlanıyor. Aynı kontrollü yürütme modeli farklı operasyon alanlarını desteklerken yetki, doğrulama ve kanıt açık kalabilir.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Çözüm kalıpları</div><h2>Yetkiyi modele taşımadan akıllı yeteneklerden yararlanın.</h2></div><p className="muted">Bu kalıplar ILAIOS ürün ve mimari yönünü açıklar. Yayınlanmış müşteri kullanımları veya genel kullanıma açık entegrasyonlar iddiası taşımaz.</p></div><div className="grid two-up">{solutions.map(([title,text,points])=><article className="card" key={title}><h3>{title}</h3><p>{text}</p><ul>{points.map(point=><li key={point}>{point}</li>)}</ul></article>)}</div></div></section>
  <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">İşletim modeli</div><h2>İstekten kabul edilmiş sonuca.</h2></div><p className="muted">Bir çözüm yalnızca prompt veya ajan değildir; yetkiyi, yürütmeyi, doğrulamayı ve kanıtı birleştiren kontrollü bir yoldur.</p></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Doğru yolu seçmek</div><h2>Model yeteneğinden değil operasyonel riskten başlayın.</h2></div><div><p className="lead small">Doğru otomasyon yolu gereken yetkiye, yan etkilerin geri alınabilirliğine, deterministik kontrollerin kalitesine ve yürütme sonrasında gereken kanıta bağlıdır.</p><p className="muted">ILAIOS, görevi karşılayabildiği yerde deterministik yürütmeyi tercih eder; akıllı yetenekleri ise değer kattıkları noktada açık sınırlar içinde kullanır.</p><div className="actions"><Link className="button secondary" href="/tr/architecture">Mimari</Link><Link className="button secondary" href="/tr/security">Güvenlik modeli</Link><Link className="text-link" href="/tr/trust">Güven Merkezi →</Link></div></div></div></section>
</>}
