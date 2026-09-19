import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Çözümler", description: "ILAIOS'un araştırma, kurumsal zekâ, iş operasyonları ve dijital üretim için yönetilen çözüm kalıplarını inceleyin.", alternates: { canonical: "/tr/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Dijital ürün çıkar", "Araştırma ve planlamadan lansmanın gerçekten ihtiyaç duyduğu web sitesi, yazılım, uygulama veya medya üretimine geç."],
  ["Dijital çıktılar üret ve güncelle", "Kullanıcıyı her çıktı için ayrı bir yapay zekâ workflow'u işletmeye zorlamadan web, yazılım ve medya teslimlerini koordine et."],
  ["Harekete geçmeden araştır", "Bir karar veya üretim işi dış bilgiye bağlıysa kaynakları, belirsizliği ve doğrulamayı görünür tut."],
  ["Tekrarlanabilir işi otomatikleştir", "Deterministik adımları ve akıllı yetenekleri birleştirirken izinleri, onayları ve kabul koşullarını açık tut."],
] as const;

const operatingModel = [
  ["01", "Sonucu tarif et", "Araç listesinden değil, istediğin sonuçtan başla."],
  ["02", "Gereken işi çözümle", "ILAIOS uygulanabilir yetenekleri ve üretim yollarını belirler."],
  ["03", "Sınırlar içinde yürüt", "Kimlik, politika, onaylar ve sınırlandırılmış araçlar kabul edilmiş işi kısıtlar."],
  ["04", "Teslimden önce doğrula", "Kabul kontrolleri sonucun bitmiş olarak teslim edilip edilemeyeceğini belirler."],
] as const;

export default function Page(){return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">Çözümler</div><h1>Araç zincirinden değil, sonuçtan başla.</h1><p className="lead">ILAIOS bir hedefin gerektirdiği araştırma, planlama, üretim ve doğrulamayı tek yönetilen ürün sınırı altında koordine etmek üzere tasarlanıyor.</p><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Sonuç kalıpları</div><h2>Farklı hedefler aynı kontrollü yürütme modelini yeniden kullanabilir.</h2></div><p className="muted">Bu örnekler ürün yönünü anlatır; her entegrasyonun veya uçtan uca yolun bugün genel kullanıma açık olduğu iddiasını taşımaz.</p></div><div className="principle-directory">{solutions.map(([title,text],index)=><article key={title}><span>{String(index+1).padStart(2,"0")}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">Tek çalışma modeli</div><h2>Talep edilen sonuçtan doğrulanmış teslime.</h2></div></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Doğru görünümü seç</div><h2>Bireysel ve kurumsal kullanım aynı platformu paylaşır; ürün hikâyesi aynı değildir.</h2></div><div className="actions"><Link className="button secondary" href="/tr/individuals">Bireyler için</Link><Link className="button secondary" href="/tr/enterprise">Kurumlar için</Link><Link className="text-link" href="/tr/trust">Güven sınırı →</Link></div></div></section>
</>}
