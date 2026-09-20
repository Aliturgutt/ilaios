import type { Metadata } from "next";
import Link from "next/link";
import ThemedDiagram from "../../../ThemedDiagram";

export const metadata: Metadata = {
  title: "App Factory",
  description: "ILAIOS App Factory; belirli sınırlar içinde derleme, test, paketleme ve kanıt kontrolleri olan Windows öncelikli tamamlanmış ürün yoludur; Android/iOS, üretim imzalama ve mağaza yayını ayrı geçitler olarak kalır.",
  alternates: { canonical: "/tr/factories/app", languages: { tr: "/tr/factories/app", en: "/factories/app", "x-default": "/factories/app" } },
};

const stages = [
  ["01", "Ürün hedefi ve referanslar", "Uygulama sonucunu, kullanıcıları, platform hedefini, kısıtları, referansları ve kabul ölçütlerini tanımla."],
  ["02", "Ürün ve UX tanımı", "Hedefi sınırlandırılmış kullanıcı akışlarına, ekran yapısına, etkileşim yönüne, veri ihtiyaçlarına ve incelenebilir gereksinimlere dönüştür."],
  ["03", "Mimari ve kapsam", "Uygulamadan önce asgari mimariyi, korunan kökleri, izinleri, veri ve kimlik doğrulama sınırlarını ve derleme/test planını çözümle."],
  ["04", "Yönetilen uygulama", "Uygulama yalnız izin verilen kapsam içinde ilerler. Mevcut Core, politika, onay, araç ve kanıt otoriteleri değişmez."],
  ["05", "Derle, test et ve doğrula", "Sınırlandırılmış platform yolu için gerekli biçim, analiz, test, derleme ve paket kontrollerini çalıştır; kaynak ile çıktı arasındaki kesin kanıtı koru."],
  ["06", "Windows öncelikli tamamlanmış ürün", "Güncel depo kanıtı; derlenmiş, paketlenmiş ve temel çalışma testi yapılmış, sınırlandırılmış Flutter Windows uygulamasını içerik adresli kanıtla içerir."],
  ["07", "Mobil ve mağaza geçitleri", "Android/iOS yürütme, üretim imzalama, App Store/Play Store gönderimi, sertifikasyon ve canlı kurulum ayrı kanıta bağlı yayın işi olarak kalır."],
  ["08", "Teslim ve kabul kaydı", "Tamamlanan her platform kapsamı için test sonuçlarını, çıktı kimliğini, onayları ve teslim kanıtını kaydet; kanıtlanmamış yayın veya kurulum durumunu tamamlandı olarak işaretleme."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero app-factory-copy"><div className="eyebrow">ILAIOS App Factory</div><h1>Ürün fikrinden sınırlandırılmış uygulama sonucuna; yayın yetkisi açık ve ayrı kalır.</h1><p className="lead">App Factory artık yalnız inceleme ve planlama kavramı değildir: depo kanıtı, Windows öncelikli sınırlandırılmış tamamlanmış ürün yolunu içerir. Bu, Android/iOS, üretim imzalama veya mağaza yayınının tamamlandığı anlamına gelmez.</p><div className="factory-availability-banner"><p>Windows öncelikli sınırlandırılmış tamamlanmış ürün kanıtı depoda vardır. Android/iOS, imzalama, mağaza yayını, canlı kurulum ve farklı uygulama türlerinin tamamı için kapsam ayrı geçitler olarak kalır.</p></div></section>

  <section className="section surface-section factory-visual-section app-factory-visual-copy"><div className="shell"><div className="section-heading"><div><div className="eyebrow">App Factory hedef yaşam döngüsü</div><h2>Ürün fikirlerini mağazaya hazır hedeflere dönüştür; mağaza yayınını kanıtsız tamamlandı diye sunma.</h2></div><p>Sağlanan görsel hedef ürün yaşam döngüsünü anlatır. “Store Ready” mağaza hazırlığı hedefidir; imzalama, gönderim, sertifikasyon veya canlı kurulumun gerçekleştiğinin kanıtı değildir.</p></div><ThemedDiagram light="/visuals/app-light.avif" dark="/visuals/app-dark.avif" alt="ILAIOS App Factory diyagramı: istem ve referanslar, ürün ve UX tanımı, mimari, derleme, test ve doğrulama, iOS veya Android hazırlığı ve mağazaya hazır hedefi" caption="Hedef yaşam döngüsü: istem + referanslar → ürün/UX tanımı → mimari → derleme → test ve doğrulama → platform paketleme → mağaza hazırlığı. Güncel mobil/mağaza tamamlanması kanıta bağlı kalır." priority /></div></section>

  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Güncel gerçeklik ve hedef</div><h2>Windows kanıtı güncel gerçekliktir. Mobil mağaza yayını hedef iştir.</h2></div><p className="muted">Bu ayrım hedef mimarinin üretim tamamlanması gibi sunulmasını engeller.</p></div><div className="grid two-up">{stages.map(([n,t,x]) => <article className="card" key={n}><div className="eyebrow">{n}</div><h2>{t}</h2><p>{x}</p></article>)}</div></div></section>
  <section className="section"><div className="shell callout app-factory-publish-callout"><div><div className="eyebrow">Yayın sınırı</div><h2>Derleme kanıtı; imzalama, mağaza gönderimi veya yayın yetkisini sessizce vermez.</h2><p className="muted">Bu işlemler kendi kimlik bilgilerini, onayını, kesin çıktı kimliğini, platform kontrollerini ve dış kanıtını gerektirir.</p></div><div className="actions"><Link className="button" href="/tr/use-ilaios">ILAIOS nasıl kullanılır?</Link><Link className="button secondary" href="/tr/factories">Tüm factory'ler</Link></div></div></section>
</>; }
