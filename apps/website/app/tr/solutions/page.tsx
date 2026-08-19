import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Çözümler", description: "ILAIOS'un araştırma, kurumsal zekâ, iş operasyonları ve dijital üretim için yönetilen çözüm kalıplarını inceleyin.", alternates: { canonical: "/tr/solutions", languages: { en: "/solutions", tr: "/tr/solutions", "x-default": "/solutions" } } };

const solutions = [
  ["Ürün lansmanı", "Araştırma, pazar zekâsı, strateji, bütçe/risk, web, yazılım/uygulama, medya, büyüme ve ölçümü tek yönetilen yürütme modeli altında koordine etmeyi hedefler.", ["Tek iş hedefini sınırlandırılmış işlere çözümle", "Paralel yetki oluşturmadan birden çok üretim alanını birleştir", "Sonuç boyunca doğrulama ve kanıtı koru"]],
  ["Dijital iş operasyonları", "Görevleri, süreçleri, yürütme izlemeyi, istisnaları ve onay kapılı iş eylemlerini koordine eder; iş fonksiyonlarını otonom departmanlara dönüştürmez.", ["İş kurallarını model yetkisinin dışında tut", "Hassas veya geri döndürülemez eylemleri eskale et", "Operasyonel kanıtı koru"]],
  ["Araştırma ve kurumsal zekâ", "Kaynak temelli araştırma, rekabet zekâsı, KPI/performans analizi ve kanıta dayalı önerileri birleştirir.", ["Provenance görünür kalsın", "Analizi karar yetkisinden ayır", "Belirsizliği gizlemek yerine eskale et"]],
  ["Yazılım teslimi", "Web, yazılım ve uygulama işlerini deterministik kontroller, inceleme kapıları ve izlenebilir release kanıtıyla sınırlandırılmış üretim yolları olarak yapılandırır.", ["Planlamayı yürütme yetkisinden ayır", "Deterministik kalite kapıları çalıştır", "Release/deployment yetkisini ayrıca gerektir"]],
  ["İçerik ve büyüme", "Pazar zekâsı, kampanya planlama, web/video/doküman üretimi ve ölçüm odaklı büyüme akışlarını birleştirir.", ["Yayınlama yetkisini üretimden ayrı tut", "Kanıta dayalı ölçüm kullan", "Güncel entegrasyonları maturity-gated kabul et"]],
  ["Yönetilen kurumsal otomasyon", "Deterministik workflow adımlarını akıllı yeteneklerle birleştirirken politika, onay, yetkilendirme, doğrulama ve kanıtı modelin dışında tutar.", ["Kısıtları prompt dışında tanımla", "Yeterli olduğunda deterministik yürütmeyi tercih et", "Teslimden önce tamamlanmayı doğrula"]],
] as const;

const operatingModel = [
  ["1", "İş hedefi", "Kimliği doğrulanmış sonucu ve kabul kriterlerini yakala."],
  ["2", "İşi çözümle", "Gerektikçe araştırma, zekâ, operasyon, paylaşılan yetenekler ve üretim alanlarını kullan."],
  ["3", "Yürütmeyi yönet", "Politika, onaylar, tenant bağlamı, routing ve sınırlandırılmış araçlar kabul edilen her eylemi kısıtlasın."],
  ["4", "Sonucu doğrula", "Anlatısal başarı yerine sonucu kabul kriterlerine göre kontrol et."],
  ["5", "Kanıtı koru", "İnceleme, kurtarma ve hesap verebilir teslim için yeterli bağlamı sakla."],
] as const;

const launchFlow = ["İş Hedefi", "Araştırma", "Pazar / Rekabet Zekâsı", "Strateji", "Bütçe / Risk", "Web", "Yazılım / Uygulama", "Video / İçerik", "Büyüme", "Ticaret", "Ölçüm", "Kanıt"] as const;

export default function Page(){return <>
  <section className="shell page-hero"><div className="eyebrow">Çözümler</div><h1>İş hedefleri yönetilen, fonksiyonlar arası sonuçlara dönüşür.</h1><p className="lead">ILAIOS; araştırma, kurumsal zekâ, operasyon ve dijital üretimi tek yürütme yetkisi altında koordine etmek üzere tasarlanıyor. Bir çözüm departman veya prompt değildir; iş niyetinden incelenebilir kanıta uzanan yönetilen bir yoldur.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Çözüm kalıpları</div><h2>Sonuçtan başlayın; gerçekten gereken işi birleştirin.</h2></div><p className="muted">Bu kalıplar kanonik yönü ve geliştirilmekte olan ürün kapsamını anlatır. Her entegrasyonun veya fonksiyonlar arası akışın bugün production-ready olduğu iddiasını taşımaz.</p></div><div className="grid two-up">{solutions.map(([title,text,points])=><article className="card" key={title}><h3>{title}</h3><p>{text}</p><ul>{points.map(point=><li key={point}>{point}</li>)}</ul></article>)}</div></div></section>
  <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Fonksiyonlar arası örnek</div><h2>“Yeni bir SaaS ürünü çıkar.”</h2></div><p className="muted">Kanonik yön / Geliştiriliyor. Bu sıra composition modelini gösterir; tüm akışın production'da genel kullanıma açık olduğu anlamına gelmez.</p></div><div className="runtime-line">{launchFlow.map((step,index)=><div key={step}><span>{String(index+1).padStart(2,"0")}</span><strong>{step}</strong></div>)}</div></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Çalışma modeli</div><h2>İstekten kabul edilmiş sonuca tek yetki.</h2></div><p className="muted">Kurumsal Çalışma Katmanı kanonik Core'un üzerindeki workflow composition katmanıdır; ikinci orchestrator, router, Policy Engine veya runtime değildir.</p></div><div className="flow-grid">{operatingModel.map(([n,t,x])=><article className="flow-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Güncel gerçeklik</div><h2>Capability adı deployment kanıtı değildir.</h2></div><div><p className="lead small">Finans ve maliyet zekâsı bankacılık, muhasebe veya otonom CFO yetkisi anlamına gelmez. Ticaret ve satış doğrulanmış CRM, ödeme veya otonom satış yetkisi anlamına gelmez.</p><p className="muted">Production iddiası, iddia edilen spesifik yetenek için implementation, test, CI, runtime, deployment ve uçtan uca kanıt gerektirir.</p><div className="actions"><Link className="button secondary" href="/tr/capabilities">Yetenekler</Link><Link className="button secondary" href="/tr/architecture">Mimari</Link><Link className="text-link" href="/tr/trust">Güven Merkezi →</Link></div></div></div></section>
</>}
