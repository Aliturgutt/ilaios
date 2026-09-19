import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Video & Media Factory",
  description: "ILAIOS Video & Media Factory; araştırma, senaryo, sahne/shot planlama, varlıklar, yönetilen yürütme, render, validation, publishing preparation, evidence, recovery ve cost control zincirini yapılandırır.",
  alternates: { canonical: "/tr/factories/video", languages: { tr: "/tr/factories/video", en: "/factories/video", "x-default": "/factories/video" } },
};

const stages = [
  ["01", "Konu & araştırma", "Tanımlı içerik hedefinden başla; gerekli araştırmayı topla ve factual claim gereken yerde kaynak bağlamını koru."],
  ["02", "İçerik & senaryo planlama", "Brief'i structured content plan, script, continuity kısıtları ve acceptance requirements'a dönüştür."],
  ["03", "Sahne & shot planlama", "Script'i duration, composition, continuity, asset ve generation gereksinimleri olan scene/shot'lara ayır."],
  ["04", "Asset & execution planlama", "Yüklenen/üretilen varlıkları, rights/provenance, kalite/maliyet eşiklerini ve policy içindeki eligible execution resources'ı planla."],
  ["05", "Medya, voice & audio", "Görsel medya, voice, audio ve caption'ları bounded job steps üzerinden edin veya üret."],
  ["06", "Assembly & rendering", "Media artifact'i birleştir, kabul edilmiş teknik profile göre render et ve artifact identity'yi koru."],
  ["07", "Teknik & içerik validation", "Onaydan önce media properties, continuity/content requirements, policy/rights constraints ve acceptance criteria'yı kontrol et."],
  ["08", "Approval & platform adaptation", "Gerektiğinde approval al; platform-specific format, metadata, cover/thumbnail, disclosure ve scheduling data hazırla."],
  ["09", "Publish & verify", "Publishing bir side effect'tir: idempotency, rate-limit handling, delivery verification, duplicate prevention ve post-publish checks uygula."],
  ["10", "Evidence, metrics & recovery", "Provenance, validation, delivery state, cost, retry/recovery context ve metrics'i koru; provider-reported success'i final proof kabul etme."],
] as const;

const referenceGroups = [
  ["Native reference yolu", "Desktop'tan yüklenen fotoğraf, ürün veya logo tenant-bound kalır, governed reference admission'dan geçer ve kısa ömürlü güvenli URL üzerinden uygun native reference input veya frame-reference yoluna aktarılabilir."],
  ["Kişi & ürün tutarlılığı QA", "Üretilen video kabul edilmiş referanslarla karşılaştırılır; desteklenen kimlik, kişi görünümü, ürün geometrisi, renkler, materyaller ve işaretler sessizce bozulmamalıdır."],
  ["Kesin logo sadakati", "Önce native reference kullanılır. Ardından logo consistency QA çalışır. Logo kesin korunmak zorundaysa en güçlü hedef, orijinal asset ile deterministic asset-lock/overlay veya compositing ve sonra exact render üzerinde final QA'dır."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Video / Media Factory</div><h1>Referanstan teslime kadar kontrollü kalan medya yaşam döngüsü.</h1><p className="lead">Video / Media Factory; validation, evidence, recovery, publishing side effect'leri ve cost control açık kalırken içerik üretim zincirini koordine eder.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Önizleme</span><p>Repository evidence gerçek finished-product Video E2E yolunu ve bağımsız acceptance'ı içerir. Canlı sıfır maliyetli dış provider availability hâlâ doğrulanmış değildir; eligible route yoksa sistem fail closed davranmalıdır.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Video / Media Factory özeti</div><h2>Referansları incelenebilir, doğrulanmış medya hedefine dönüştür.</h2></div><p>Görsel hedef production path'i anlatır. “Verified video” etiketi yalnız exact artifact için gerekli acceptance kontrollerinin geçmesini ifade eder; her external generation route'un bugün erişilebilir olduğu sözü değildir.</p></div><ThemedDiagram light="/visuals/video-light.avif" dark="/visuals/video-dark.avif" alt="ILAIOS Video ve Media Factory diyagramı: request, referans analizi, production, verification ve delivery" caption="Hedef workflow: request → analyze references → produce → verify → deliver. External generation ve publishing ayrıca evidence-gated kalır." priority /></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Native reference & kimlik tutarlılığı</div><h2>Gerçek fotoğraf ve marka asset'leriyle kişi, ürün ve logoyu video boyunca tutarlı koru.</h2><div className="factory-status-row"><span className="availability-chip is-development">Geliştiriliyor</span><small>Authenticated reference upload/binding ve reference-aware conditioning repository'de vardır; native signed relay, doğrudan provider-reference delivery, tam consistency QA ve live certification ayrıca evidence-gated kalır.</small></div></div><p>Public deneyim basit kalır: referansı ekle ve hedefi tarif et. Provider-specific input-reference ve frame-image sözleşmeleri ürünün yönetilen sınırının arkasında kalır.</p></div><div className="grid">{referenceGroups.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><div className="callout"><div><div className="eyebrow">Hedef yönetilen zincir</div><h2>Reference → güvenli relay → native conditioning → generation → consistency QA → gerektiğinde logo asset-lock → final QA & evidence.</h2><p className="muted">Gerçek generation, CI ve live production certification exact provider yolunu ve final artifact'i kanıtlamadan bu capability evidence-backed maturity seviyesinin üzerine çıkarılmaz.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></div></section>

  <section className="section"><div className="shell"><p className="muted">Bu sayfa kanonik workflow ile güncel bounded repository truth'u birlikte anlatır. Her dış provider, publishing destination veya medya formatının bugün genel kullanıma açık olduğunu iddia etmez.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Provider-independent by design</div><h2>Execution resources değişebilir; workflow authority'nin kaynağına dönüşmez.</h2><p className="muted">Public product experience kullanıcıya provider seçtirmez. Eligibility, policy, cost ve quality ürün sınırının arkasında yönetilir.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/platform/evidence">Evidence modeli</Link></div></div></section>
</>; }
