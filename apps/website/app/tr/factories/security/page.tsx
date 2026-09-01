import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Security Factory",
  description: "ILAIOS Security Factory; yetkili kod, secret, supply-chain, infrastructure ve local/test web güvenlik analizini remediation, retest ve bağımsız doğrulama ile sınırlandırılmış savunma workflow'unda birleştirir.",
  alternates: { canonical: "/tr/factories/security", languages: { en: "/factories/security", tr: "/tr/factories/security", "x-default": "/factories/security" } },
};

const stages = [
  ["01", "Scope'u yetkilendir", "Yalnız açıkça yetkilendirilmiş repository veya yapılandırılmış localhost/test hedefi kabul edilir. Güvenlik rolü scope'u kendi başına genişletemez."],
  ["02", "Static analysis", "Source riski, secret, dependency/supply-chain ve infrastructure configuration için bounded savunma kontrolleri çalıştırılır."],
  ["03", "Web/API observation", "Yalnız yapılandırılmış local/test hedefler için sağlanan HTTP observation'ları doğrulanır; rastgele dış ağ taraması bu factory sınırının dışındadır."],
  ["04", "Finding sınıflandır", "Finding tipi, severity bağlamı, etkilenen hedef ve evidence incelenebilir tutulur; güvenlik yalnız model hükmüne indirgenmez."],
  ["05", "Yetki içinde remediate et", "Yalnız aktif workflow ve permission modelinin izin verdiği bounded remediation önerilir veya uygulanır."],
  ["06", "Retest", "Remediation sonrası uygulanabilir deterministik kontroller tekrarlanır ve before/after evidence birbirine bağlanır."],
  ["07", "Bağımsız doğrula", "Security verification, finding'i üreten veya remediate eden rolden ayrı kalır."],
  ["08", "Durdur veya teslim et", "Eksik authorization veya çözülmemiş gate durumunda fail-closed; acceptance geçerse incelenebilir finding ve evidence teslim edilir."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Security Factory</div><h1>Yetki, evidence ve verifier ayrımıyla sınırlandırılmış savunma güvenliği analizi.</h1><p className="lead">Security Factory, ILAIOS repository'sinde doğrulanmış bounded defensive factory'dir. Yetkili code, secret, supply-chain, infrastructure ve local/test web-security kontrollerini remediation, retest ve bağımsız verification sınırlarıyla birleştirir.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Savunma sınırı</div><h2>Security capability, sınırsız tarama yetkisi anlamına gelmez.</h2></div><p className="muted">Mevcut doğrulanmış factory bilinçli olarak fail-closed tasarlanmıştır. Rastgele sistem exploit etmez, dış pentest yetkisi vermez ve SOC 2, ISO 27001 veya başka external certification iddiası oluşturmaz.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Security governance</div><h2>Permissions, DLP, evidence ve bağımsız verification aynı kontrol zincirinin parçası olarak kalır.</h2></div><div className="actions"><Link className="button" href="/tr/security">Güvenlik modeli</Link><Link className="button secondary" href="/tr/security/permissions">İzin sınırları</Link><Link className="text-link" href="/tr/agents">Ajan organizasyonu →</Link></div></div></section>
</>; }
