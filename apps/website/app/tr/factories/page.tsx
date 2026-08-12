import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ILAIOS Factory'leri",
  description: "Web, yazılım, medya, güvenlik, araştırma, doküman, büyüme ve kişisel operasyon alanlarındaki kontrollü ILAIOS factory iş akışlarını inceleyin.",
  alternates: { canonical: "/tr/factories", languages: { tr: "/tr/factories", en: "/factories", "x-default": "/factories" } },
};

const factories = [
  ["Web Factory", "Gereksinim ve bilgi mimarisinden doğrulama ve deployment hazırlığına uzanan kontrollü web üretimi.", "/tr/factories/web"],
  ["Software Factory", "Deterministik kalite kapıları ve izlenebilir teslim bağlamıyla sınırlandırılmış mühendislik workflow'ları.", "/tr/factories/software"],
  ["Video / Media Factory", "Planlama, asset, render, doğrulama ve yayın hazırlığını yapılandıran medya üretimi.", "/tr/factories/video"],
  ["Security Factory", "Açık scope, remediation evidence ve bağımsız verification sınırlarıyla yetkili savunma analizleri.", "/tr/factories/security"],
  ["Research & Data Factory", "Önerilen iddiaları doğrulanmış gerçeklerden ayıran provenance-first araştırma ve deterministik sınırlı analiz.", "/tr/factories/research-data"],
  ["Creative & Document Factory", "Güvenilir kaynaklardan doküman oluşturma, deterministik hash ve onay kapılı export projection.", "/tr/factories/creative-document"],
  ["Commerce & Growth Factory", "Sınırlı taslak kanallarıyla evidence destekli review-only büyüme önerileri; paid spend veya yayın yetkisi yoktur.", "/tr/factories/commerce-growth"],
  ["Personal Operations Factory", "Checklist, reminder, note, calendar ve email draft gibi işlemler için review-only kişisel operasyon planları.", "/tr/factories/personal-operations"],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Factory'leri</div><h1>Tek yönetişim modeli altında uzman üretim ve operasyon workflow'ları.</h1><p className="lead">ILAIOS factory'leri farklı iş türlerini kontrolsüz tek seferlik üretim yerine sınırlandırılmış workflow'lara dönüştürür. Her detay sayfası neyin uygulanmış olduğunu, hangi adımların onay istediğini ve mevcut foundation'ın açıkça neyi yapmadığını belirtir.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Factory haritası</div><h2>İş alanını seçin; kontrol ve sınırlarını inceleyin.</h2></div><p className="muted">Factory adı tek başına maturity anlamına gelmez. Public sayfalar bounded implemented foundation ile daha geniş ürün workflow'larını ayırır; repository evidence desteklemiyorsa external mutation, publishing, spend veya availability iddiası yapmaz.</p></div><div className="grid two-up">{factories.map(([title,text,href]) => <Link className="detail-link-card" href={href} key={href}><span>Factory</span><h3>{title}</h3><p>{text}</p><strong>İncele →</strong></Link>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Aynı Core tarafından yönetilir</div><h2>Yetki, validation, evidence ve recovery model anlatımından ayrı kalır.</h2></div><div className="actions"><Link className="button" href="/tr/core">Core'u incele</Link><Link className="button secondary" href="/tr/capabilities">Yetenek haritası</Link></div></div></section>
</>; }
