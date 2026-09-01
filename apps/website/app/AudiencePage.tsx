import Link from "next/link";

type Locale = "en" | "tr";
type Audience = "enterprise" | "individuals";

const copy = {
  en: {
    enterprise: {
      eyebrow: "For enterprises",
      title: "Govern intelligent work without turning model output into operational authority.",
      lead: "ILAIOS is designed for organizations that need repeatable production and automation with explicit identity, policy, validation, evidence and bounded recovery.",
      focusLabel: "Enterprise control",
      focusTitle: "Governance surrounds execution instead of living inside prompt instructions.",
      outcomes: [["Operational fragmentation", "Bring recurring research and production work into an explicit job, policy and evidence model."], ["Unbounded AI usage", "Keep model output separate from permission, approval and acceptance."], ["Production overhead", "Use separate Web, Software, App and Video/Media workflows instead of one generic generation surface."], ["Knowledge fragmentation", "Connect authorized context and project memory without making memory an authority source."], ["Audit gaps", "Associate material changes with provenance, validation and recovery history."], ["Failure ambiguity", "Bound retry and repair; stop or escalate when acceptance cannot be established."]],
      operating: [["01", "Admit work", "Identity, tenant, project context and risk define the operating boundary."], ["02", "Route capabilities", "Factories and services receive only the scope required for the job."], ["03", "Validate independently", "Required checks and approvals decide whether outputs advance."], ["04", "Retain evidence", "Material events and acceptance context remain reviewable."]],
      cta: "Explore enterprise architecture",
    },
    individuals: {
      eyebrow: "For individuals",
      title: "Describe the outcome without becoming the operator of an internal AI stack.",
      lead: "ILAIOS is designed to move personal goals through governed research, web, software, media and operations workflows while keeping state, boundaries and acceptance visible.",
      focusLabel: "Outcome first",
      focusTitle: "Less tool choreography. More reviewable progress toward the result.",
      outcomes: [["Research", "Structure sources, claims and uncertainty instead of relying on an opaque one-shot answer."], ["Website work", "Move through requirements, design, implementation and QA toward a verified finished site."], ["Software work", "Keep engineering changes bounded by repository context, tests and review gates."], ["Application work", "Keep current review-only App Factory boundaries explicit while the broader outcome remains canonical direction."], ["Media production", "Coordinate research, script, assets, render and validation through a governed workflow."], ["Personal operations", "Prepare reviewable plans without silently widening authority."]],
      operating: [["01", "State the goal", "Describe what should be finished instead of selecting internal models."], ["02", "Bound context", "Identity, project context and permissions define what may participate."], ["03", "Execute and validate", "Capabilities work inside scope; required checks decide acceptance."], ["04", "Review the result", "Outcome, state and evidence stay visible instead of disappearing into narration."]],
      cta: "Explore how ILAIOS works",
    },
  },
  tr: {
    enterprise: {
      eyebrow: "Kurumlar için",
      title: "Model çıktısını operasyonel yetkiye dönüştürmeden akıllı işleri yönetin.",
      lead: "ILAIOS; tekrarlanabilir üretim ve otomasyon için kimlik, politika, doğrulama, kanıt ve sınırlandırılmış kurtarmayı açık tutacak şekilde tasarlanır.",
      focusLabel: "Kurumsal kontrol",
      focusTitle: "Yönetim, prompt talimatlarının içinde değil yürütmenin çevresindedir.",
      outcomes: [["Operasyon parçalanması", "Tekrarlanan araştırma ve üretim işlerini açık iş, politika ve kanıt modeline bağlayın."], ["Sınırsız AI kullanımı", "Model çıktısını izin, onay ve kabulden ayrı tutun."], ["Üretim yükü", "Tek genel üretim ekranı yerine Web, Yazılım, Uygulama ve Video/Medya iş akışlarını ayrı tutun."], ["Bilgi parçalanması", "Yetkili bağlamı ve proje hafızasını hafızayı yetki kaynağı yapmadan bağlayın."], ["Denetim boşlukları", "Önemli değişiklikleri kaynak kökeni, doğrulama ve kurtarma geçmişiyle ilişkilendirin."], ["Hata belirsizliği", "Yeniden deneme ve düzeltmeyi sınırlandırın; kabul kurulamıyorsa durdurun veya yükseltin."]],
      operating: [["01", "İşi kabul et", "Kimlik, tenant, proje bağlamı ve risk çalışma sınırını belirler."], ["02", "Yetenekleri yönlendir", "Üretim alanları ve servisler yalnız iş için gereken kapsamı alır."], ["03", "Bağımsız doğrula", "Gerekli kontroller ve onaylar çıktının ilerleyip ilerleyemeyeceğini belirler."], ["04", "Kanıtı koru", "Önemli olaylar ve kabul bağlamı incelenebilir kalır."]],
      cta: "Kurumsal mimariyi incele",
    },
    individuals: {
      eyebrow: "Bireysel kullanıcılar için",
      title: "İç AI yığınının operatörü olmadan sonucu tarif edin.",
      lead: "ILAIOS; kişisel hedefleri yönetilen araştırma, web, yazılım, medya ve operasyon iş akışlarına taşırken durum, sınırlar ve kabulü görünür tutmak için tasarlanır.",
      focusLabel: "Önce sonuç",
      focusTitle: "Daha az araç koordinasyonu. Sonuca doğru daha incelenebilir ilerleme.",
      outcomes: [["Araştırma", "Tek seferlik opak yanıt yerine kaynakları, iddiaları ve belirsizliği yapılandırın."], ["Web sitesi", "Gereksinim, tasarım, geliştirme ve QA üzerinden doğrulanmış bitmiş siteye ilerleyin."], ["Yazılım", "Mühendislik değişikliklerini repository bağlamı, testler ve inceleme kapılarıyla sınırlandırın."], ["Uygulama", "Daha geniş uygulama sonucu kanonik yön olarak kalırken mevcut inceleme odaklı App Factory sınırlarını açık tutun."], ["Medya üretimi", "Araştırma, senaryo, varlık, render ve doğrulamayı yönetilen iş akışıyla koordine edin."], ["Kişisel operasyon", "Yetkiyi sessizce genişletmeden incelenebilir planlar hazırlayın."]],
      operating: [["01", "Hedefi söyle", "İç model seçmek yerine neyin bitmesini istediğinizi tarif edin."], ["02", "Bağlamı sınırla", "Kimlik, proje bağlamı ve izinler neyin kullanılabileceğini belirler."], ["03", "Yürüt ve doğrula", "Yetenekler kapsam içinde çalışır; gerekli kontroller kabulü belirler."], ["04", "Sonucu incele", "Sonuç, durum ve kanıt model anlatımının içinde kaybolmadan görünür kalır."]],
      cta: "ILAIOS nasıl çalışır?",
    },
  },
} as const;

export default function AudiencePage({ locale, audience }: { locale: Locale; audience: Audience }) {
  const c = copy[locale][audience];
  const base = locale === "tr" ? "/tr" : "";
  const detailHref = audience === "enterprise" ? `${base}/architecture` : `${base}/how-it-works`;
  return <>
    <section className={`shell audience-hero audience-${audience}`}><div><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1></div><div><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/factories`}>{locale === "tr" ? "Üretim alanları" : "Factories"}</Link><Link className="button secondary" href={detailHref}>{c.cta}</Link></div></div></section>
    <section className="section"><div className="shell audience-focus"><div><span className="micro-label">{c.focusLabel}</span><h2>{c.focusTitle}</h2></div><div className="audience-outcome-list">{c.outcomes.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{title}</strong><p>{text}</p></div></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">{locale === "tr" ? "Çalışma modeli" : "Operating model"}</div><h2>{locale === "tr" ? "Basit istek, açık kontroller." : "Simple request, explicit controls."}</h2></div></div><div className="audience-process">{c.operating.map(([n, title, text]) => <article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
    <section className="section compact-section"><div className="shell status-note"><span>{locale === "tr" ? "Ürün gerçeği" : "Product truth"}</span><p>{locale === "tr" ? "Kanonik ürün yönü ile güncel uygulama, doğrulama, deployment ve genel kullanıma açıklık durumu ayrı tutulur." : "Canonical product direction remains distinct from current implementation, verification, deployment and general availability."}</p></div></section>
  </>;
}
