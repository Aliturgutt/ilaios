import Link from "next/link";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "About ILAIOS",
    title: "Building a governed operating system for finished digital outcomes.",
    lead: "ILAIOS is an independent technology company developing a product model where authority, execution, validation, evidence and recovery are designed as one operating system.",
    missionLabel: "What we are building",
    mission: "One product brain coordinates multiple native factories while models, tools and providers remain replaceable execution resources.",
    principlesLabel: "Operating principles",
    principles: [["Control before convenience", "Automation does not widen authority simply because a model can act."], ["Evidence before confidence", "Important outcomes show what happened, what passed and why they were accepted."], ["Architecture before interface", "Web, Desktop, Mobile and other clients remain projections of backend authority."]],
    founderLabel: "Founder",
    founder: "Ali Turgut",
    founderText: "Ali Turgut founded ILAIOS and leads product direction across governed intelligent automation, secure execution, native production workflows and evidence-driven systems.",
    truthLabel: "Product truth",
    truth: "ILAIOS is under active development. Public materials deliberately separate canonical product direction from current implementation, verification, deployment and general availability.",
    solutions: "Solutions",
    architecture: "Architecture",
  },
  tr: {
    eyebrow: "ILAIOS Hakkında",
    title: "Bitmiş dijital sonuçlar için yönetilen bir işletim sistemi geliştiriyoruz.",
    lead: "ILAIOS; yetki, yürütme, doğrulama, kanıt ve kurtarmayı tek bir çalışma modeli içinde tasarlayan bağımsız bir teknoloji şirketidir.",
    missionLabel: "Ne geliştiriyoruz?",
    mission: "Tek ürün beyni, birden çok yerleşik üretim alanını koordine eder; modeller, araçlar ve sağlayıcılar değiştirilebilir yürütme kaynakları olarak kalır.",
    principlesLabel: "Çalışma ilkeleri",
    principles: [["Kolaylıktan önce kontrol", "Bir model işlem yapabiliyor diye otomasyon yetkiyi genişletmez."], ["Güvenden önce kanıt", "Önemli sonuçlar ne olduğunu, neyin geçtiğini ve neden kabul edildiğini gösterebilir."], ["Arayüzden önce mimari", "Web, Masaüstü, Mobil ve diğer istemciler arka uç yetkisinin görünümüdür."]],
    founderLabel: "Kurucu",
    founder: "Ali Turgut",
    founderText: "Ali Turgut, ILAIOS'u kurdu ve yönetilen akıllı otomasyon, güvenli yürütme, yerleşik üretim iş akışları ve kanıta dayalı sistemlerin ürün yönünü yönetiyor.",
    truthLabel: "Ürün gerçeği",
    truth: "ILAIOS aktif geliştirme aşamasındadır. Kamuya açık içerikler kanonik ürün yönünü güncel uygulama, doğrulama, yayın ve genel kullanıma açıklık durumundan bilinçli olarak ayırır.",
    solutions: "Çözümler",
    architecture: "Mimari",
  },
} as const;

export default function AboutPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell about-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell about-editorial-grid">
      <article className="about-mission"><span className="micro-label">{c.missionLabel}</span><h2>{c.mission}</h2></article>
      <div className="about-principles"><span className="micro-label">{c.principlesLabel}</span>{c.principles.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{text}</p></div></article>)}</div>
    </div></section>
    <section className="section surface-section"><div className="shell founder-row" id="founder"><div><span className="micro-label">{c.founderLabel}</span><h2>{c.founder}</h2></div><p>{c.founderText}</p></div></section>
    <section className="section compact-section"><div className="shell about-truth"><div><span className="micro-label">{c.truthLabel}</span><p>{c.truth}</p></div><div className="actions"><Link className="button" href={`${base}/solutions`}>{c.solutions}</Link><Link className="button secondary" href={`${base}/architecture`}>{c.architecture}</Link></div></div></section>
  </>;
}
