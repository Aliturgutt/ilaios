import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Commerce & Growth Factory | Türkçe",
  description: "ILAIOS Commerce & Growth Factory; güvenilir evidence, sınırlı draft kanalları ve sıfır paid-spend authority ile review-only büyüme önerileri üreten bounded foundation'dır.",
  alternates: { canonical: "/tr/factories/commerce-growth", languages: { tr: "/tr/factories/commerce-growth", en: "/factories/commerce-growth", "x-default": "/factories/commerce-growth" } },
};

const stages = [
  ["01", "Güvenilir evidence kaydet", "Açık source locator ve SHA-256 digest tut; untrusted veya unknown evidence bir proposal'ı destekleyemez."],
  ["02", "Objective ve audience tanımla", "Plan; broad marketing authority varsaymak yerine objective, audience ve bounded channel'larını kaydeder."],
  ["03", "İzinli draft kanallarını kullan", "Implemented foundation yalnız content draft, email draft, social draft ve sales-enablement proposal kanallarını destekler."],
  ["04", "Paid spend'i engelle", "Sıfırdan büyük paid-spend isteği fail closed olur; billing, ad buying ve budget mutation bu factory'nin dışındadır."],
  ["05", "Review için onayla", "Deterministik plan digest tutulur; review projection açılmadan önce proposal açıkça onaylanmalıdır."],
  ["06", "Publishing mutation yok", "External commerce veya growth mutation mevcut implementation tarafından açıkça yasaklanır."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Commerce & Growth Factory</div><h1>Gizli spend veya publishing authority olmadan evidence destekli büyüme proposal'ları.</h1><p className="lead">Commerce & Growth Factory bounded implemented foundation'dır. Güvenilir evidence üzerinden deterministik review-only growth plan üretir, kanalları desteklenen draft/sales-enablement çıktılarıyla sınırlar, review için approval ister ve paid spend ya da external mutation'ı reddeder.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-only growth workflow</div><h2>Planlama; spend, publish ve account mutation'dan ayrılır.</h2></div><p className="muted">Bu foundation ad-network execution, otomatik outreach, billing authority veya autonomous campaign publishing iddiası yapmaz.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Tasarımdan gelen sınırlar</div><h2>External action öncesinde trusted evidence ve açık review gate vardır.</h2></div><div className="actions"><Link className="button" href="/tr/factories">Tüm factory'ler</Link><Link className="button secondary" href="/tr/security">Güvenlik modeli</Link></div></div></section>
</>; }
