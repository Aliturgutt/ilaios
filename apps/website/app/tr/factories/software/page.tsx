import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../../ThemedDiagram";

export const metadata: Metadata = {
  title: "Software Factory",
  description: "ILAIOS Software Factory; software delivery'yi bounded implementation, tests, review, security gates, release evidence ve recovery içeren governed engineering jobs olarak yapılandırır.",
  alternates: { canonical: "/tr/factories/software", languages: { tr: "/tr/factories/software", en: "/factories/software", "x-default": "/factories/software" } },
};

const stages = [
  ["01", "Specify", "İstenen sonucu, repository veya system boundary'yi, kısıtları, acceptance criteria'yı, riski ve gerekli evidence'i tanımla."],
  ["02", "Plan", "İşi dependencies, ownership, permissions ve validation planı olan bounded engineering jobs'a ayır."],
  ["03", "Değiştirmeden önce incele", "Blind edit yerine mümkün olduğunda source, symbol, dependency, configuration ve runtime context kullan."],
  ["04", "Kapsam içinde implement et", "Engineering capabilities yalnız yetkili dosya ve sistemleri değiştirir; architecture ve security boundaries otoriter kalır."],
  ["05", "Test & review", "Acceptance öncesi uygulanabilir deterministic tests, lint/type/static checks, code review ve security checks çalıştır."],
  ["06", "Bağımsız doğrula", "Material work yalnız author veya executing process başarı bildirdi diye kabul edilmez. Gerekli independent verification risk-driven kalır."],
  ["07", "Release preparation", "Artifact'leri versionla, build/test/security evidence'i yakala, rollback/recovery semantics hazırla ve environment progression'ı açık tut."],
  ["08", "Deliver & reconcile", "Source/build/deployment preparation'ı traceable evidence ile teslim et; failures bounded diagnose, repair, retest, retry veya rollback yollarını izler."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS Software Factory</div><h1>Açık sınırlar ve acceptance gate'leri olan yazılım mühendisliği.</h1><p className="lead">Software Factory, software hedeflerini unrestricted one-shot code generation yerine governed engineering work'e dönüştürür.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Önizleme</span><p>Bounded local Windows finished-product kapsamı repository-verified durumdadır. Keyfi external-repository effects, software breadth veya commercial release bu evidence tarafından ima edilmez.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Software Factory özeti</div><h2>Gereksinimleri test edilmiş, incelenebilir yazılım değişikliklerine dönüştür.</h2></div><p>Hedef görsel; requirement, implementation, tests, review, bounded repair ve handoff aşamalarını görünür tutar; bir code diff'i completion saymaz.</p></div><ThemedDiagram light="/visuals/software-light.avif" dark="/visuals/software-dark.avif" alt="ILAIOS Software Factory diyagramı: requirement and context, scope and plan, implementation, tests, review, bounded repair ve tested change" caption="Hedef workflow: requirement + context → scope & plan → implement → test → review → bounded repair → tested change." priority /></div></section>

  <section className="section"><div className="shell"><p className="muted">ILAIOS capability maturity ile release state'i ayrı takip eder. Bounded bir scope için repository verification, her Software Factory fonksiyonunun veya external effect'in bugün genel kullanıma açık olduğu anlamına gelmez.</p><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Governed delivery</div><h2>Implementation, verification, merge ve release authority risk gerektirdiğinde ayrı kalır.</h2><p className="muted">Test edilmiş değişiklik otomatik olarak merged, deployed veya production-verified değildir. Bu geçişlerin her biri ayrı evidence ister.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/platform/validation">Validation modeli</Link></div></div></section>
</>; }
