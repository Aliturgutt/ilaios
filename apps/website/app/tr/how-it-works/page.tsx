import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../ThemedDiagram";

export const metadata: Metadata = {
  title: "ILAIOS Nasıl Çalışır",
  description: "ILAIOS'un sonuç tarifinden yönetilen yürütme, doğrulama ve teslime uzanan public ürün akışını görün.",
  alternates: { canonical: "/tr/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const steps = [
  ["01", "Bitmesini istediğin sonucu tarif et", "Sonuç, referanslar ve kısıtlarla başla. Dahili model, ajan veya sağlayıcı zincirini seçmek zorunda değilsin."],
  ["02", "ILAIOS işi düzenler", "Sistem talebi sınırlandırılmış işe dönüştürür ve bu iş için gereken izin, politika ve onayları uygular."],
  ["03", "İş üretilir", "Uygulanabilir yetenekler web, yazılım, medya, araştırma veya bunların birleşiminde kabul edilmiş işi yürütür."],
  ["04", "ILAIOS doğrular ve teslim eder", "Gerekli kontroller sonucun kabul edilip edilmeyeceğini belirler. Geçerse bitmiş sonuç ve ilgili kanıt teslim edilir; çözülemeyen iş anlatımla başarıya dönüştürülmez."],
] as const;

const verified = [
  ["Çalışıyor", "Gerekli işlev veya sonuç gerçekten mevcut."],
  ["Uygun", "Sonuç belirtilen kabul ölçütlerine göre kontrol edildi."],
  ["Güvenli", "Uygulanabilir politika, güvenlik ve izin kontrolleri korunuyor."],
  ["İzlenebilir", "Kabul edilen sonuç, teslim edilen işi incelemek için gereken kanıtı koruyor."],
] as const;

export default function Page() {
  return <>
    <section className="shell page-hero compact-page-hero"><div className="eyebrow">ILAIOS Nasıl Çalışır</div><h1>Ne istediğini söyle. ILAIOS işi doğrulanmış sonuca kadar yönetir.</h1><p className="lead">Public deneyim bilinçli olarak sadedir: bitmiş sonucu tarif et, ILAIOS işi yönetsin ve yürütsün, sonucu da yalnız gerekli kontroller geçtikten sonra teslim alsın.</p><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS'u kullan</Link></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Dört adım</div><h2>Tek sonuçtan bitmiş işe.</h2></div><p>Kullanıcının sağlayıcı, worker ID veya dahili routing kararı vermesi gerekmez.</p></div><div className="journey-grid">{steps.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Ürün akışı</div><h2>Hedef → yönetilen iş → üretim → doğrulama → teslim.</h2></div><p>Diyagram kullanıcıya dönük ürün yolunu gösterir. Dahili sağlayıcı ve yürütme ayrıntıları ürün sınırının arkasında kalır.</p></div><ThemedDiagram light="/visuals/general-flow-light.avif" dark="/visuals/general-flow-dark.avif" alt="ILAIOS public iş akışı: tarif edilen hedeften yönetilen yürütme, üretim, doğrulama ve teslime" caption="Public ürün akışı: kullanıcı sonucu tarif eder; ILAIOS yönetilen işi yürütür ve teslimden önce sonucu doğrular." priority /></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Doğrulanmış ne demek?</div><h2>Doğrulama pratik bir soruyu yanıtlar: bu sonuç kabul edilmeye hazır mı?</h2></div><div><p className="lead small">Kontroller üretilen işe göre değişir. Gerekli kabul kontrolleri yalnız işi bitmiş saymak için atlanamaz.</p><div className="verification-list">{verified.map(([title,text],i)=><div key={title}><span>{String(i+1).padStart(2,"0")}</span><strong>{title}</strong><small>{text}</small></div>)}</div></div></div></section>
    <section className="section compact-section"><div className="shell callout"><div><div className="eyebrow">Teknik modeli mi arıyorsun?</div><h2>Public akış sade kalır; mimari incelenebilir olmaya devam eder.</h2><p className="muted">Architecture, Core ve Security; ana ürün yolunu dahili ayrıntılarla doldurmadan kontrol ve kanıt modelini açıklar.</p></div><div className="actions"><Link className="button secondary" href="/tr/architecture">Mimari</Link><Link className="button secondary" href="/tr/core">Core</Link></div></div></section>
  </>;
}
