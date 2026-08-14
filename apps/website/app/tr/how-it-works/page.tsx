import type { Metadata } from "next";
import Link from "next/link";
import CanonicalSystemDetail from "../../CanonicalSystemDetail";

export const metadata: Metadata = {
  title: "ILAIOS Nasıl Çalışır",
  description: "ILAIOS'un tek hedefi kimlik, policy, bounded execution, tek routing kararı, bağımsız validation, evidence ve recovery ile nasıl kontrollü işe dönüştürdüğünü görün.",
  alternates: { canonical: "/tr/how-it-works", languages: { en: "/how-it-works", tr: "/tr/how-it-works", "x-default": "/how-it-works" } },
};

const simple = [
  ["01", "Bitmiş sonucu tarif et", "Kullanıcı internal model, agent veya provider seçmek yerine neyin tamamlanması gerektiğini söyler."],
  ["02", "ILAIOS yürütme sözleşmesini kurar", "Kimlik, tenant/proje bağlamı, gereksinimler, kabul ölçütleri ve yetkili bağlam sınırlandırılmış hedefi tanımlar."],
  ["03", "Yönetilen iş yürütülür", "Admission, gerektiğinde onay, TEK RoutingDecision ve sınırlandırılmış worker'lar kabul edilmiş görevleri ilerletir."],
  ["04", "Bağımsız kontroller finali belirler", "Validation, evidence, bounded repair ve final evaluation sonucun kabul edilip edilmeyeceğini veya güvenli şekilde duracağını belirler."],
] as const;

const verified = ["Fonksiyonel kontroller", "Browser QA", "Güvenlik kontrolleri", "Erişilebilirlik", "Performans", "SEO", "Visual QA", "Exact artifact identity", "Evidence / provenance", "İstenmişse deployment validation"] as const;

export default function Page() {
  return <>
    <section className="shell page-hero"><div className="eyebrow">ILAIOS Nasıl Çalışır</div><h1>Yüzeyde basit. Altta kontrollü.</h1><p className="lead">Kanonik deneyim; giriş ve tek doğal dil hedefinden, kullanıcıya internal model/provider/agent/tool stack'ini işlettirmeden kabul edilmiş sonuca ilerler.</p></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Kullanıcı akışı</div><h2>Sonuç → yönetilen yürütme → bağımsız kabul → bitmiş iş.</h2></div><p className="muted">Bu kanonik ürün yönüdür. Güncel kullanılabilirlik; implementation, test, CI, runtime ve deployment kanıtıyla ayrıca ispatlanır.</p></div><div className="journey-grid">{simple.map(([n,t,x]) => <article className="journey-card" key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></div></section>
    <section className="section surface-section"><div className="shell"><CanonicalSystemDetail locale="tr" variant="journey" /></div></section>
    <section className="section"><div className="shell"><CanonicalSystemDetail locale="tr" variant="runtime" /></div></section>
    <section className="section surface-section"><div className="shell"><CanonicalSystemDetail locale="tr" variant="recovery" /></div></section>
    <section className="section"><div className="shell"><CanonicalSystemDetail locale="tr" variant="cost" /></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">Verified ne demek?</div><h2>“Doğrulanmış bitmiş ürün” slogan değil, acceptance modelidir.</h2></div><div><p className="lead small">Final evaluation, gerekli alan ölçütlerini tamamlanmış artifact veya işlem sonucuna uygular. Mümkün olduğunda üreten worker/model kendi final sonucunun tek doğrulayıcısı olmaz.</p><div className="verification-list">{verified.map((item,i)=><div key={item}><span>{String(i+1).padStart(2,"0")}</span><strong>{item}</strong></div>)}</div></div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">Prompt gösterisi değil, kontrollü sistem</div><h2>Execution ancak gerekli kontroller ve evidence geçtiğinde kabul edilir.</h2><p className="muted">Policy/security reddi policy bypass edilerek onarılamaz. Repair; deneme, maliyet ve süre sınırları içindedir; çözülemeyen iş durur veya yükseltilir.</p></div><div className="actions"><Link className="button" href="/tr/core">ILAIOS Core'u incele</Link><Link className="button secondary" href="/tr/architecture">Mimari</Link></div></div></section>
  </>;
}
