import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Software Factory",
  description: "ILAIOS Software Factory'nin yazılım teslimini sınırlandırılmış implementation, test, review, security gate, release evidence ve recovery içeren kontrollü engineering job'larına dönüştüren yaklaşımı.",
  alternates: { canonical: "/tr/factories/software", languages: { en: "/factories/software", tr: "/tr/factories/software", "x-default": "/factories/software" } },
};

const stages = [
  ["01", "Tanımla", "İstenen sonucu, repository veya sistem sınırını, kısıtları, kabul kriterlerini, riski ve gerekli evidence'ı tanımla."],
  ["02", "Planla", "İşi bağımlılık, sorumluluk, izin ve validation planı olan sınırlandırılmış engineering job'larına böl."],
  ["03", "Değiştirmeden önce incele", "Kör değişiklik yerine mümkün olduğunda source, symbol, dependency, configuration ve runtime bağlamını kullan."],
  ["04", "Scope içinde uygula", "Engineering yetenekleri yalnız izinli dosya ve sistemleri değiştirir; architecture ve security sınırları otorite olarak kalır."],
  ["05", "Test & review", "Kabul öncesi uygulanabilir deterministik test, lint/type/static kontrol, code review ve security kontrollerini çalıştır."],
  ["06", "Bağımsız doğrula", "Önemli iş yalnız yazarı veya yürüten ajan başarılı dediği için kabul edilmez. Gereken independent verification risk seviyesine göre uygulanır."],
  ["07", "Release hazırlığı", "Artifact'ları versionla, build/test/security evidence'ını kaydet, rollback veya recovery semantiğini hazırla ve environment progression'ı açık tut."],
  ["08", "Teslim & reconcile", "Source/build/deployment hazırlığını izlenebilir evidence ile teslim et; hatalar sınırlı diagnose, repair, retest, retry veya rollback yolunu izler."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Software Factory</div><h1>Açık sınırlar ve kabul kapılarıyla yazılım mühendisliği.</h1><p className="lead">Software Factory, yazılım hedeflerini kontrolsüz tek seferlik kod üretimi yerine yönetilen engineering işlerine dönüştürmek için tasarlanan ILAIOS yeteneğidir.</p></section>
  <section className="section"><div className="shell"><p className="muted">ILAIOS capability maturity ile release state'i ayrı izler. Bu sayfa kanonik ürün workflow'unu açıklar; tüm Software Factory fonksiyonlarının bugün genel kullanıma açık olduğunu iddia etmez.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Kontrollü teslim</div><h2>Risk gerektiğinde üretim, doğrulama ve release otoritesi birbirinden ayrı kalır.</h2></div><div className="actions"><Link className="button" href="/tr/platform/validation">Validation modeli</Link><Link className="button secondary" href="/tr/how-it-works">ILAIOS nasıl çalışır</Link></div></div></section>
</>; }
