import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ILAIOS Nasıl Çalışır",
  description: "ILAIOS'un tek bir sonuç tarifini policy, sınırlandırılmış execution, bağımsız validation, evidence, teslim, izleme ve recovery ile nasıl kontrollü işe dönüştürdüğünü görün.",
  alternates: { canonical: "/tr/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const simple = [
  ["01", "Bitmiş sonucu tarif et", "Kullanıcı internal model, agent veya provider seçmek yerine neyin tamamlanması gerektiğini söyler."],
  ["02", "ILAIOS execution'ı yönetir", "Platform yetkiyi çözer, sınırlandırılmış işi planlar ve uygun deterministik veya akıllı capability'leri yönlendirir."],
  ["03", "Gerekli kontroller kabulü belirler", "Validation, evidence ve approvals sonucun ilerleyip ilerleyemeyeceğini belirler."],
  ["04", "Kabul edilmiş işi al", "Finished-product workflow incelenebilir sonuç üretir; dış side effect'ler ayrıca kontrollü kalır."],
] as const;

const steps = [
  ["01", "Hedef & güvenilir bağlam", "Kullanıcı veya kurum hedefi tanımlar. Kimlik, tenant, proje ve doğrulanmış bağlam çalışma sınırını belirler."],
  ["02", "Policy & authorization", "Execution öncesinde araç kapsamı, hedefler, risk, bütçe ve onay gereksinimleri çözülür."],
  ["03", "Planla & orkestre et", "İş sıralı ve sınırlandırılmış job'lara bölünür; deterministik servislere veya akıllı yeteneklere yönlendirilir."],
  ["04", "Scope içinde yürüt", "Ajanlar, skill'ler, worker'lar ve araçlar yalnız verilen yetki içinde çalışır. İstemciler backend state'inin projection'ıdır."],
  ["05", "Bağımsız doğrula", "Schema, test, policy kontrolü, teknik probe ve kabul kriterleri sonucun ilerleyip ilerleyemeyeceğini belirler."],
  ["06", "Evidence & onay", "Önemli işlemler, doğrulama sonuçları, provenance ve kararlar korunur. Policy gerektiğinde insan onayı zorunludur."],
  ["07", "Teslim & izle", "Kabul edilen artifact veya operasyonel sonuç teslim, deployment ya da yayın hazırlığına geçer ve izlenebilir kalır."],
  ["08", "Kurtar & denetle", "Retry edilebilir hatalar sınırlı recovery izler. Diğer hatalar incelenebilir evidence ile durur veya escalation'a gider."],
] as const;

const verified = ["Fonksiyonel kontroller", "Browser QA", "Güvenlik kontrolleri", "Erişilebilirlik", "Performans", "SEO", "Visual QA", "Exact artifact identity", "Evidence", "İstenmişse deployment validation"] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">ILAIOS Nasıl Çalışır</div><h1>Yüzeyde basit. Altta kontrollü.</h1><p className="lead">Kanonik deneyim, kullanıcıya internal model/provider/agent/tool stack'ini işlettirmeden tarif edilen sonuçtan kabul edilmiş işe ilerler.</p></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Kullanıcı akışı</div><h2>Sonuç → execution → validation → bitmiş iş.</h2></div><p className="muted">Bu ürün yönüdür; her factory fonksiyonunun bugün genel kullanıma açık olduğu iddiası değildir.</p></div><div className="journey-grid">{simple.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section architecture-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Governance yolu</div><h2>Reasoning ile otorite ayrı kalır.</h2></div><p className="muted">Model ve ajanlar sınırlandırılmış işi önerebilir veya yürütebilir; policy, authorization, durable state, validation, evidence, approvals ve recovery platform tarafından yönetilir.</p></div><div className="grid two-up">{steps.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Verified ne demek?</div><h2>“Doğrulanmış bitmiş ürün” slogan değil, acceptance modelidir.</h2></div><div><p className="lead small">Kontroller iş alanına göre değişir. Bir web sitesi için acceptance öncesinde aşağıdaki evidence aileleri uygulanabilir.</p><div className="verification-list">{verified.map((item,i)=><div key={item}><span>{String(i+1).padStart(2,"0")}</span><strong>{item}</strong></div>)}</div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Prompt gösterisi değil, kontrollü sistem</div><h2>Execution ancak gerekli kontroller ve evidence geçtiğinde kabul edilir.</h2><p className="muted">Bu model sessiz veya kontrolsüz hata riskini azaltır; yazılımın, modellerin, sağlayıcıların veya altyapının hiçbir zaman hata yapmayacağını iddia etmez.</p></div><div className="actions"><Link className="button" href="/tr/core">ILAIOS Core'u incele</Link><Link className="button secondary" href="/tr/architecture">Mimari</Link></div></div></section>
  </>;
}
