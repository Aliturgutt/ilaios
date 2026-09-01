import Link from "next/link";
import FactoryExplorer from "./FactoryExplorer";
import SystemVisuals from "./SystemVisuals";
import CanonicalSystemDetail from "./CanonicalSystemDetail";
import ThemedDiagram from "./ThemedDiagram";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "ILAIOS Factories",
    title: "Specialized production paths under one governance model.",
    lead: "Factories turn different kinds of work into bounded, inspectable workflows instead of one generic generation surface.",
    orchestrationTitle: "One request can resolve to the right production path.",
    orchestrationLead: "The public product surface shows the factory decision and governed result without exposing internal provider routing or credentials.",
    orchestrationCaption: "Public factory-orchestration view: goal, understanding, governed orchestration, execution and verification across specialized production paths.",
    lifecycleTitle: "Different domains specialize the workflow without creating a second runtime.",
    lifecycleLead: "Request, scope, decomposition, execution, validation and delivery remain governed by the same platform authority and evidence chain.",
    compositionTitle: "One goal may compose multiple factories without creating parallel authority.",
    compositionLead: "Cross-factory planning is a bounded DAG under the same Core. A goal can coordinate research, web, software, media or document work while policy, routing, state, evidence and recovery stay shared.",
    composition: [["Goal", "Outcome + acceptance"], ["Plan", "Bounded cross-factory DAG"], ["Factories", "Specialized domain workflows"], ["Validation", "Domain + final checks"], ["Evidence", "One accepted outcome trail"]],
    knowledgeTitle: "Knowledge/RAG is shared infrastructure, not a tenth factory.",
    knowledgeLead: "Authorized project context and source provenance can inform multiple factories while retrieval remains tenant-, principal-, project- and purpose-aware.",
    note: "A factory name does not imply every target capability is deployed or generally available. Preview and In development labels keep current public readiness separate from the target workflow.",
    core: "One Core governs identity, policy, capability resolution, validation, evidence and recovery across the factory layer.",
    coreCta: "Explore Core",
    capCta: "Capability map",
  },
  tr: {
    eyebrow: "ILAIOS Üretim Alanları",
    title: "Tek yönetim modeli altında uzmanlaşmış üretim yolları.",
    lead: "Her factory, farklı işleri tek bir genel üretim ekranına sıkıştırmak yerine sınırlandırılmış ve incelenebilir bir iş akışına dönüştürür.",
    orchestrationTitle: "Tek istek doğru üretim yoluna çözümlenebilir.",
    orchestrationLead: "Public ürün yüzeyi factory kararını ve yönetilen sonucu gösterir; dahili provider routing veya credential ayrıntılarını dışarı açmaz.",
    orchestrationCaption: "Public factory orchestration görünümü: hedef, anlama, yönetilen orkestrasyon, yürütme ve uzmanlaşmış üretim yollarında doğrulama.",
    lifecycleTitle: "Farklı alanlar iş akışını uzmanlaştırır; ikinci bir runtime oluşturmaz.",
    lifecycleLead: "Talep, kapsam, ayrıştırma, yürütme, doğrulama ve teslim aynı platform yetkisi ve kanıt zinciri altında kalır.",
    compositionTitle: "Tek hedef birden fazla factory'yi birleştirebilir; paralel yetki oluşturmaz.",
    compositionLead: "Cross-factory planning aynı Core altında bounded DAG olarak kalır. Araştırma, web, yazılım, medya veya doküman işi birlikte yürütülebilir; policy, routing, state, evidence ve recovery paylaşılır.",
    composition: [["Hedef", "Sonuç + kabul"], ["Plan", "Bounded cross-factory DAG"], ["Factory'ler", "Uzmanlaşmış alan iş akışları"], ["Doğrulama", "Alan + final kontroller"], ["Kanıt", "Tek kabul edilmiş sonuç izi"]],
    knowledgeTitle: "Knowledge/RAG onuncu factory değil, paylaşılan altyapıdır.",
    knowledgeLead: "Yetkili proje bağlamı ve kaynak provenance birden çok factory'yi besleyebilir; retrieval tenant, principal, proje ve amaca göre yetkilendirilmiş kalır.",
    note: "Bir factory adı, hedeflenen her yeteneğin bugün yayında veya genel kullanıma açık olduğu anlamına gelmez. Önizleme ve Geliştiriliyor etiketleri public readiness ile hedef workflow'u ayrı tutar.",
    core: "Kimlik, politika, capability resolution, doğrulama, kanıt ve kurtarma tüm factory'lerde aynı Core tarafından yönetilir.",
    coreCta: "Core'u incele",
    capCta: "Yetenek haritası",
  },
} as const;

export default function FactoriesPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p></section>
    <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Factory orkestrasyonu" : "Factory orchestration"}</div><h2>{c.orchestrationTitle}</h2></div><p>{c.orchestrationLead}</p></div><ThemedDiagram light="/visuals/factory-orchestration-light.avif" dark="/visuals/factory-orchestration-dark.avif" alt={locale === "tr" ? "ILAIOS hedefinin Web, App, Software, Video, Research ve multi-factory üretim yollarına yönetilen şekilde yönlendirilmesini gösteren factory orchestration diyagramı" : "ILAIOS factory-orchestration diagram showing one goal resolving to Web, App, Software, Video, Research and multi-factory production paths"} caption={c.orchestrationCaption} priority /></div></section>
    <section className="section"><div className="shell"><FactoryExplorer locale={locale} /></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{locale === "tr" ? "Factory yaşam döngüsü" : "Factory lifecycle"}</div><h2>{c.lifecycleTitle}</h2></div><p>{c.lifecycleLead}</p></div><SystemVisuals locale={locale} variant="factory" /></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Cross-factory composition</div><h2>{c.compositionTitle}</h2></div><p>{c.compositionLead}</p></div><div className="runtime-line">{c.composition.map(([title, detail], index) => <div key={title}><span>{String(index + 1).padStart(2, "0")}</span><strong>{title}</strong><small>{detail}</small></div>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Knowledge / RAG</div><h2>{c.knowledgeTitle}</h2></div><p>{c.knowledgeLead}</p></div><CanonicalSystemDetail locale={locale} variant="knowledge" /></div></section>
    <section className="section compact-section"><div className="shell factory-truth-note"><span>{locale === "tr" ? "Ürün gerçeği" : "Product truth"}</span><p>{c.note}</p></div></section>
    <section className="section compact-section surface-section"><div className="shell compact-cta"><div><div className="eyebrow">ILAIOS Core</div><h2>{c.core}</h2></div><div className="actions"><Link className="button" href={`${base}/core`}>{c.coreCta}</Link><Link className="button secondary" href={`${base}/capabilities`}>{c.capCta}</Link></div></div></section>
  </>;
}
