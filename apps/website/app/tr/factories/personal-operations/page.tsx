import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Personal Operations Factory | Türkçe",
  description: "ILAIOS Personal Operations Factory; checklist, reminder, note, calendar ve email draft gibi deterministik review-only kişisel operasyon planları için bounded foundation'dır.",
  alternates: { canonical: "/tr/factories/personal-operations", languages: { tr: "/tr/factories/personal-operations", en: "/factories/personal-operations", "x-default": "/factories/personal-operations" } },
};

const stages = [
  ["01", "Sınırlandırılmış objective tanımla", "Open-ended kişisel automation isteği yerine açık ve boş olmayan step'lere sahip isimlendirilmiş plan oluştur."],
  ["02", "Yalnız draft action kullan", "Mevcut implementation yalnız calendar, checklist, email, note ve reminder draft action'larını destekler."],
  ["03", "Payload'ları hash'le", "Her step payload için SHA-256 digest tutulur; review projection content'i sessizce değiştirmeden deterministik evidence korur."],
  ["04", "Unsafe action'da fail closed", "Unsupported action, duplicate step ID, missing plan ve geçersiz state transition authority genişletmek yerine işlemi durdurur."],
  ["05", "Review için onayla", "Review projection açılmadan önce plan açık bir approver almalıdır."],
  ["06", "External account mutation yok", "Mevcut foundation planı dış kişisel sistem veya hesaplara uygulamayı açıkça yasaklar."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Personal Operations Factory</div><h1>Herhangi bir dış sisteme dokunmadan önce incelenebilir kalan kişisel automation planları.</h1><p className="lead">Personal Operations Factory deterministik review-only planlar için bounded implemented foundation'dır. Küçük bir draft action setini destekler, step payload'larını hash'ler, açık review approval ister ve external personal system mutation'ını yasaklar.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Review-first kişisel operasyon</div><h2>Automation niyeti otomatik olarak account authority'ye dönüşmez.</h2></div><p className="muted">Mevcut implementation email göndermez, calendar event oluşturmaz, reminder değiştirmez veya external account'a yazmaz. Review için bounded draft plan hazırlar.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Açık insan sınırı</div><h2>Draft, evidence ve approval gelecekteki external execution yolundan önce görünür kalır.</h2></div><div className="actions"><Link className="button" href="/tr/factories">Tüm factory'ler</Link><Link className="button secondary" href="/tr/individuals">Bireysel kullanım</Link></div></div></section>
</>; }
