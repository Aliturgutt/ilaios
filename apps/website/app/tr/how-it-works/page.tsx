import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ILAIOS Nasıl Çalışır",
  description: "ILAIOS'un hedefleri kimlik, policy, orchestration, sınırlandırılmış execution, doğrulama, evidence, onay, teslim, izleme ve recovery ile nasıl kontrollü işe dönüştürdüğünü görün.",
  alternates: { canonical: "/tr/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const steps = [
  ["01", "Hedef & güvenilir bağlam", "Kullanıcı veya kurum hedefi tanımlar. Kimlik, tenant, proje ve doğrulanmış bağlam çalışma sınırını belirler."],
  ["02", "Policy & authorization", "Hassas execution öncesinde araç kapsamı, hedefler, risk, bütçe ve onay gereksinimleri çözülür."],
  ["03", "Planla & orkestre et", "İş sıralı ve sınırlandırılmış job'lara bölünür; deterministik servislere veya akıllı yeteneklere yönlendirilir."],
  ["04", "Scope içinde yürüt", "Ajanlar, skill'ler, worker'lar ve araçlar yalnız verilen yetki içinde çalışır. İstemciler backend state'inin projection'ıdır."],
  ["05", "Bağımsız doğrula", "Schema, test, policy kontrolü, teknik probe ve kabul kriterleri sonucun ilerleyip ilerleyemeyeceğini belirler."],
  ["06", "Evidence & onay", "Önemli işlemler, doğrulama sonuçları, provenance ve kararlar korunur. Policy gerektiğinde insan onayı zorunludur."],
  ["07", "Teslim & izle", "Kabul edilen artifact veya operasyonel sonuç teslim, deployment ya da yayın hazırlığına geçer ve izlenebilir kalır."],
  ["08", "Kurtar & denetle", "Retry edilebilir hatalar sınırlı recovery izler. Diğer hatalar incelenebilir evidence ile durur veya escalation'a gider."],
] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">ILAIOS Nasıl Çalışır</div><h1>Bir hedeften kontrollü ve incelenebilir sonuca.</h1><p className="lead">ILAIOS reasoning ile otoriteyi ayırır. Model ve ajanlar öneri üretebilir veya sınırlandırılmış işi yürütebilir; policy, authorization, kalıcı state, validation, evidence, approvals ve recovery platform tarafından yönetilir.</p></section>
    <section className="section"><div className="shell"><div className="grid two-up">{steps.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Prompt gösterisi değil, kontrollü sistem</div><h2>Execution ancak gerekli kontroller ve evidence geçtiğinde kabul edilir.</h2><p className="muted">Bu model sessiz veya kontrolsüz hata riskini azaltır; yazılımın, modellerin, sağlayıcıların veya altyapının hiçbir zaman hata yapmayacağını iddia etmez.</p></div><div className="actions"><Link className="button" href="/tr/core">ILAIOS Core'u incele</Link><Link className="button secondary" href="/tr/architecture">Mimari</Link></div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Uzman factory'ler</div><h2>Tekrarlanabilir üretim akışları aynı governance modelini paylaşır.</h2></div></div><div className="grid three-up"><Link className="card card-link" href="/tr/factories/web"><h3>Web Factory</h3><p>Gereksinim → bilgi mimarisi → geliştirme → QA → deployment hazırlığı.</p></Link><Link className="card card-link" href="/tr/factories/software"><h3>Software Factory</h3><p>Plan → sınırlandırılmış engineering → test → review → release evidence.</p></Link><Link className="card card-link" href="/tr/factories/video"><h3>Video / Media Factory</h3><p>Araştırma → senaryo → sahne → medya → render → validation → yayın hazırlığı.</p></Link></div></div></section>
  </>;
}
