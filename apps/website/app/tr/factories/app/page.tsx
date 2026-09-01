import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../../ThemedDiagram";

export const metadata: Metadata = {
  title: "App Factory",
  description: "ILAIOS App Factory; deterministik build, test, package ve evidence kontrolleri olan Windows-first bounded finished-product yoludur; Android/iOS, production signing ve Store publication ayrı gate'ler olarak kalır.",
  alternates: { canonical: "/tr/factories/app", languages: { tr: "/tr/factories/app", en: "/factories/app", "x-default": "/factories/app" } },
};

const stages = [
  ["01", "Ürün hedefi & referanslar", "Uygulama sonucunu, kullanıcıları, platform hedefini, kısıtları, referansları ve acceptance criteria'yı tanımla."],
  ["02", "Product & UX specification", "Hedefi bounded user flows, screen structure, interaction direction, data needs ve incelenebilir requirements'a dönüştür."],
  ["03", "Architecture & scope", "Implementation öncesi minimum architecture, protected roots, permissions, data/auth boundaries ve build/test planını çözümle."],
  ["04", "Governed implementation", "Implementation yalnız admitted scope içinde ilerler. Mevcut Core, policy, approval, tool ve evidence authorities değişmez."],
  ["05", "Build, test & verify", "Bounded platform yolu için gerekli format/analyze/test/build/package kontrollerini çalıştır ve exact source-to-artifact evidence'i koru."],
  ["06", "Windows-first finished product", "Güncel repository evidence; build edilmiş, packaged ve smoke-tested bounded generated Flutter Windows uygulamasını content-addressed evidence ile içerir."],
  ["07", "Mobile & Store gate'leri", "Android/iOS execution, production signing, App Store/Play Store submission, certification ve live install ayrı evidence-gated release işi olarak kalır."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS App Factory</div><h1>Ürün fikrinden bounded uygulama sonucuna; release authority açık kalır.</h1><p className="lead">App Factory artık yalnız review-plan konsepti değildir: repository evidence bounded Windows-first finished-product yolunu içerir. Bu, Android/iOS, production signing veya Store publication'ın tamamlandığı anlamına gelmez.</p><div className="factory-availability-banner"><span className="availability-chip is-preview">Önizleme</span><p>Windows-first bounded finished-product evidence repository'de vardır. Android/iOS, signing, Store publication, live install ve arbitrary-app breadth ayrı gate'ler olarak kalır.</p></div></section>

  <section className="section surface-section factory-visual-section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">App Factory hedef yaşam döngüsü</div><h2>Ürün fikirlerini Store-ready hedeflere dönüştür; Store publication'ı kanıtsız tamamlandı diye sunma.</h2></div><p>Sağlanan görsel hedef ürün yaşam döngüsünü anlatır. “Store Ready” release-readiness hedefidir; signing, submission, certification veya live install'ın gerçekleştiğinin kanıtı değildir.</p></div><ThemedDiagram light="/visuals/app-light.avif" dark="/visuals/app-dark.avif" alt="ILAIOS App Factory diyagramı: prompt ve referanslar, product ve UX specification, architecture, build, test ve verify, iOS veya Android preparation ve Store Ready hedefi" caption="Hedef yaşam döngüsü: prompt + references → product/UX spec → architecture → build → test & verify → platform packaging → Store readiness. Güncel mobile/Store completion evidence-gated kalır." priority /></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Current reality + target truth</div><h2>Windows evidence güncel gerçekliktir. Mobile Store release hedef iştir.</h2></div><p className="muted">Bu ayrım target architecture'ın production completion gibi sunulmasını engeller.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout"><div><div className="eyebrow">Release boundary</div><h2>Build evidence; signing, Store submission veya publication authority'yi sessizce vermez.</h2><p className="muted">Bu işlemler kendi credential, approval, exact artifact identity, platform checks ve external evidence'ini gerektirir.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/factories">Tüm factory'ler</Link></div></div></section>
</>; }
