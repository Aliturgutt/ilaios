import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "App Factory",
  description: "ILAIOS App Factory; doğrudan client mutation, deployment, signing veya store submission yetkisi olmadan Windows, Android ve iOS için deterministik review-only değişiklik, build ve test planları hazırlayan sınırlandırılmış bir foundation'dır.",
  alternates: { canonical: "/tr/factories/app", languages: { tr: "/tr/factories/app", en: "/factories/app", "x-default": "/factories/app" } },
};

const stages = [
  ["01", "Desteklenen client platformunu seç", "Mevcut bounded foundation yalnız Windows, Android ve iOS planlama taleplerini kabul eder."],
  ["02", "Sınırlandırılmış istek oluştur", "Desteklenen işlemler açık hedef ve artifact yolu olan review odaklı client change, build ve test planlarıdır."],
  ["03", "Client root'larını koru", "Desktop, mobile veya website implementation root'larını hedefleyen talepler doğrudan kaynak değiştirmek yerine fail closed olur."],
  ["04", "İsteği deterministik hash'le", "Eşdeğer istekler aynı SHA-256 request digest'ini üretir; review projection için kararlı evidence sağlanır."],
  ["05", "Review için onay iste", "Yalnız açıkça onaylanmış istekler review projection üretebilir."],
  ["06", "Release yetkisini engelle", "Doğrudan client mutation, deployment, signing ve app-store submission bu foundation'ın açıkça dışındadır."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS App Factory</div><h1>Client mutation veya release öncesinde sert sınırlar ve deterministik evidence ile uygulama planlama.</h1><p className="lead">App Factory, ILAIOS platformundaki bounded implemented foundation'lardan biridir. Desteklenen client platformları için deterministik review-only istekler hazırlar; implementation root'ları, deployment, signing ve store submission yetkisini kendi dışında tutar.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-only app workflow</div><h2>Planlama, implementation ve dağıtım yetkisinden ayrı kalır.</h2></div><p className="muted">Repository testleri deterministik istekleri, approval gate'i, korunan client root'larını ve fail-closed deployment/signing/store sınırlarını açıkça doğrular.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Sınırlandırılmış tasarım</div><h2>App Factory kontrollü review artifact'leri hazırlar; sessizce bir release pipeline'ına dönüşmez.</h2></div><div className="actions"><Link className="button" href="/tr/factories">Tüm factory'ler</Link><Link className="button secondary" href="/tr/desktop">Desktop</Link></div></div></section>
</>; }
