import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Video & Media Factory",
  description: "ILAIOS Video & Media Factory'nin araştırma, senaryo, sahne/shot planı, asset, provider routing, ses, render, validation, yayın hazırlığı, evidence, recovery ve maliyet kontrolü içeren akışı.",
  alternates: { canonical: "/tr/factories/video", languages: { en: "/factories/video", tr: "/tr/factories/video", "x-default": "/factories/video" } },
};

const stages = [
  ["01", "Konu & araştırma", "Tanımlı içerik hedefinden başla, gerekli araştırmayı topla ve factual claim içeren akışlarda kaynak bağlamını koru."],
  ["02", "İçerik & senaryo planı", "Brief'i yapılandırılmış içerik planına, senaryoya, continuity kısıtlarına ve kabul gereksinimlerine dönüştür."],
  ["03", "Sahne & shot planı", "Senaryoyu süre, composition, continuity, asset ve generation gereksinimleri olan sahne ve shot'lara böl."],
  ["04", "Asset & provider planı", "Yüklenen/üretilen asset'ları, rights/provenance, provider seçimini, maliyet/kalite eşiklerini ve fallback yollarını planla."],
  ["05", "Medya, voice & audio", "Görsel medya, voice, audio ve caption'ları değiştirilebilir provider'lar ve sınırlandırılmış job adımlarıyla edin veya üret."],
  ["06", "Assembly & render", "Episode veya medya artifact'ını birleştir, seçilen teknik profilde render et ve artifact kimliğini koru."],
  ["07", "Teknik & içerik validation", "Onay öncesi medya özelliklerini, continuity/içerik gereksinimlerini, policy/rights sınırlarını ve kabul kriterlerini doğrula."],
  ["08", "Onay & platform adaptasyonu", "Gerektiğinde onay al; platforma özel format, metadata, cover/thumbnail, disclosure ve schedule verisini hazırla."],
  ["09", "Publish & verify", "Publishing bir side effect'tir: idempotency, rate-limit handling, delivery verification, duplicate prevention ve post-publish kontrolü uygula."],
  ["10", "Evidence, metrik & recovery", "Provenance, validation, delivery state, maliyet, retry/recovery bağlamı ve metrikleri koru; provider 'success' mesajını tek başına final kanıt sayma."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Video / Media Factory</div><h1>Araştırmadan teslimata kadar kontrollü kalan medya yaşam döngüsü.</h1><p className="lead">Video / Media Factory, provider seçimi, validation, evidence, recovery, publishing side effect'leri ve maliyet kontrollerini açık tutarak uçtan uca içerik üretim zincirini koordine etmek için tasarlanan ILAIOS yeteneğidir.</p></section>
  <section className="section"><div className="shell"><p className="muted">Bu sayfa kanonik workflow'u ve doğrulanmış mimari yönü açıklar. Her provider, yayın hedefi veya factory fonksiyonunun bugün genel kullanıma açık olduğunu iddia etmez.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Provider bağımsız tasarım</div><h2>Generation provider'ları değişebilir; workflow otoritesinin kaynağı olamaz.</h2></div><div className="actions"><Link className="button" href="/tr/how-it-works">ILAIOS nasıl çalışır</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></section>
</>; }
