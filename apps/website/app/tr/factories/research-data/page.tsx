import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Araştırma & Veri Factory",
  description: "ILAIOS Araştırma & Veri Factory; kaynak kaydı, iddia doğrulama, deterministik sayısal analiz ve yalnız doğrulanmış gerçeklerin bilgi yapısına aktarımı için provenance-first bounded workflow sağlar.",
  alternates: { canonical: "/tr/factories/research-data", languages: { en: "/factories/research-data", tr: "/tr/factories/research-data", "x-default": "/factories/research-data" } },
};

const stages = [
  ["01", "Kanıtı kaydet", "Açıkça sağlanan kaynak içeriğini locator, sabit source ID, trust flag, metadata ve SHA-256 içerik özetiyle kaydeder."],
  ["02", "İddia öner", "Bir iddiayı fact statüsünden ayrı tutar ve desteklenmemiş model anlatımı yerine bilinen source ID'lere bağlanmasını zorunlu kılar."],
  ["03", "Desteği doğrula", "Bir iddia verified olmadan önce yapılandırılmış minimum trusted bağımsız kaynak sayısını ister; mevcut bounded uygulamanın varsayılanı ikidir."],
  ["04", "Fail-closed çalış", "Bilinmeyen kaynak, duplicate evidence ID, yetersiz trusted destek ve geçersiz analiz girdileri gate'i sessizce zayıflatmak yerine workflow'u durdurur."],
  ["05", "Deterministik analiz et", "Bounded sayısal girdilerde canonical values digest ile count, minimum, maximum ve mean saklanır; tekrar analiz aynı sonucu üretir."],
  ["06", "Doğrulanmış bilgiyi projekte et", "Yalnız verified iddialar Fact node olabilir; Evidence node'ları ve derived-from edge'leri provenance bağını korur."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Araştırma & Veri Factory</div><h1>İddia, kaynak ve doğrulama sınırlarını görünür tutan araştırma.</h1><p className="lead">Araştırma & Veri Factory, ILAIOS repository'sinde uygulanmış bounded bir temeldir. Kaynak provenance'ını kaydeder, önerilen iddiaları verified fact'lerden ayırır, bounded sayısal analizleri deterministik yürütür ve evidence gereksinimleri karşılanmadığında fail-closed davranır.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Provenance-first</div><h2>Bir araştırma çıktısı yalnız model ürettiği için gerçek kabul edilmez.</h2></div><p className="muted">Mevcut uygulama rastgele dış kaynakları otonom biçimde taramaz ve genel amaçlı research coverage iddiası oluşturmaz. Açıkça sağlanan evidence üzerinde çalışır ve iddiaları yalnız yapılandırılmış trusted-source gate'leri geçtiğinde doğrulanmış statüye taşır.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Bağlı bilgi</div><h2>Doğrulanmış gerçekler, türetildikleri evidence ile bağlı kalır.</h2></div><div className="actions"><Link className="button" href="/tr/capabilities">Yetenekleri incele</Link><Link className="button secondary" href="/tr/core">ILAIOS Core'u incele</Link><Link className="text-link" href="/tr/architecture">Mimari →</Link></div></div></section>
</>; }
