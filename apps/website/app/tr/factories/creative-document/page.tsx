import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Creative & Document Factory | Türkçe",
  description: "ILAIOS Creative & Document Factory; güvenilir kaynaklarla doküman oluşturma, deterministik provenance ve onay kapılı export için bounded implemented foundation'dır.",
  alternates: { canonical: "/tr/factories/creative-document", languages: { tr: "/tr/factories/creative-document", en: "/factories/creative-document", "x-default": "/factories/creative-document" } },
};

const stages = [
  ["01", "Güvenilir kaynakları kaydet", "Açık source ID, locator ve SHA-256 content digest tut; kaynak güveni bounded input state'in parçası olarak korunur."],
  ["02", "Deterministik oluştur", "Boş olmayan bölümler ve bilinen güvenilir source ID'lerle metin artifact'i oluştur; sabit body digest üret."],
  ["03", "Provenance hatasında fail closed", "Bilinmeyen, duplicate veya untrusted source referansları evidence gereksinimini sessizce zayıflatmak yerine işlemi durdurur."],
  ["04", "Onay iste", "Oluşturulan artifact açık bir approval geçişi yapılana kadar onaysız kalır."],
  ["05", "Projection export et", "Yalnız onaylı artifact; title, body, body digest ve source provenance içeren projection üretebilir."],
  ["06", "External mutation yok", "Mevcut foundation deterministik text artifact ve projection üretir; harici sisteme publish, send veya mutation yapmaz."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Creative & Document Factory</div><h1>Güvenilir kaynak, deterministik provenance ve approval gate ile doküman üretimi.</h1><p className="lead">Creative & Document Factory, ILAIOS repository'sinde bounded implemented foundation olarak yer alır. Açıkça kaydedilmiş güvenilir kaynaklardan text artifact oluşturur, source/body içeriğini hash'ler, desteklenmeyen provenance'ı engeller ve yalnız approval sonrası export eder.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Sınırlandırılmış doküman workflow'u</div><h2>Draft üretimi sessizce yayın yetkisine dönüşmez.</h2></div><p className="muted">Mevcut implementation bilerek dardır. Arbitrary document-format üretimi, external publishing veya autonomous distribution iddiası yapmaz.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Kontrollü çıktı</div><h2>Onaylı projection, artifact'i oluşturan source trail'i korur.</h2></div><div className="actions"><Link className="button" href="/tr/factories">Tüm factory'ler</Link><Link className="button secondary" href="/tr/capabilities">Yetenekler</Link></div></div></section>
</>; }
