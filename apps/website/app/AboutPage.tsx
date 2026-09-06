import Link from "next/link";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "About ILAIOS",
    title: "Building a governed operating system for finished digital outcomes.",
    lead: "ILAIOS is a product initiative focused on connecting authority, execution, validation, evidence and recovery in one governed operating model.",
    missionLabel: "What we are building",
    mission: "One control model coordinates the work while models, tools and providers remain replaceable execution resources rather than separate authorities.",
    principlesLabel: "Operating principles",
    principles: [["Control before convenience", "Automation stays inside explicit authority."], ["Evidence before claims", "Important outcomes remain reviewable before they are presented as accepted."], ["One authority across surfaces", "Product clients connect to the same governed backend instead of creating independent execution authority."]],
    founderLabel: "Founder",
    founder: "Ali Turgut",
    founderText: "Ali Turgut founded ILAIOS and leads its product direction, with a focus on governed automation, finished-product workflows and evidence-backed execution.",
    truthLabel: "Product truth",
    truth: "ILAIOS is under active development. Public materials separate product direction from what is currently implemented, verified, deployed and generally available.",
    solutions: "Explore outcomes",
    architecture: "Architecture",
  },
  tr: {
    eyebrow: "ILAIOS Hakkında",
    title: "Bitmiş dijital sonuçlar için yönetilen bir işletim sistemi geliştiriyoruz.",
    lead: "ILAIOS; yetki, yürütme, doğrulama, kanıt ve kurtarmayı tek yönetilen çalışma modeli içinde birleştirmeye odaklanan bir ürün girişimidir.",
    missionLabel: "Ne geliştiriyoruz?",
    mission: "Tek kontrol modeli işi koordine eder; modeller, araçlar ve sağlayıcılar ayrı otoriteler değil, değiştirilebilir yürütme kaynakları olarak kalır.",
    principlesLabel: "Çalışma ilkeleri",
    principles: [["Kolaylıktan önce kontrol", "Otomasyon açık yetki sınırları içinde kalır."], ["İddiadan önce kanıt", "Önemli sonuçlar kabul edilmiş olarak sunulmadan önce incelenebilir kalır."], ["Tüm yüzeylerde tek otorite", "Ürün istemcileri bağımsız yürütme otoritesi oluşturmak yerine aynı yönetilen arka uca bağlanır."]],
    founderLabel: "Kurucu",
    founder: "Ali Turgut",
    founderText: "Ali Turgut, ILAIOS'u kurdu ve ürün yönünü; yönetilen otomasyon, bitmiş ürün iş akışları ve kanıta dayalı yürütme odağıyla yönetiyor.",
    truthLabel: "Ürün gerçeği",
    truth: "ILAIOS aktif geliştirme aşamasındadır. Kamuya açık içerikler ürün yönünü bugün gerçekten uygulanmış, doğrulanmış, yayınlanmış ve genel kullanıma açık olan durumdan ayırır.",
    solutions: "Sonuçları keşfet",
    architecture: "Mimari",
  },
} as const;

const heroTitleStyle = {
  fontSize: "clamp(2.25rem, 4.2vw, 4rem)",
  lineHeight: 1.02,
  letterSpacing: "-0.045em",
  maxWidth: "15ch",
} as const;

const missionTitleStyle = {
  fontSize: "clamp(1.75rem, 2.8vw, 2.8rem)",
  lineHeight: 1.08,
  letterSpacing: "-0.035em",
  maxWidth: "18ch",
} as const;

export default function AboutPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell about-intro"><div><div className="eyebrow">{c.eyebrow}</div><h1 style={heroTitleStyle}>{c.title}</h1></div><p className="lead">{c.lead}</p></section>
    <section className="section"><div className="shell about-editorial-grid">
      <article className="about-mission"><span className="micro-label">{c.missionLabel}</span><h2 style={missionTitleStyle}>{c.mission}</h2></article>
      <div className="about-principles"><span className="micro-label">{c.principlesLabel}</span>{c.principles.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{text}</p></div></article>)}</div>
    </div></section>
    <section className="section surface-section"><div className="shell founder-row" id="founder"><div><span className="micro-label">{c.founderLabel}</span><h2>{c.founder}</h2></div><p>{c.founderText}</p></div></section>
    <section className="section compact-section"><div className="shell about-truth"><div><span className="micro-label">{c.truthLabel}</span><p>{c.truth}</p></div><div className="actions"><Link className="button" href={`${base}/solutions`}>{c.solutions}</Link><Link className="button secondary" href={`${base}/architecture`}>{c.architecture}</Link></div></div></section>
  </>;
}
