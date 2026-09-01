import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "ILAIOS Core", description: "ILAIOS Core'un yetki, doğrulama, kanıt ve recovery modelini inceleyin.", alternates: { canonical: "/tr/core", languages: { tr: "/tr/core", en: "/core", "x-default": "/core" } } };

const flow = [
  ["01", "Hedef ve bağlam", "İstenen sonuç; çalışma sınırını belirleyen kimlik, proje bağlamı ve kısıtlarla birlikte sisteme girer."],
  ["02", "Kontrol", "Politika, izinler ve onaylar hassas yürütmeden önce işin ne yapabileceğini belirler."],
  ["03", "Planla ve yürüt", "İş parçalara ayrılır ve sınırlandırılmış yeteneklere yönlendirilir; model veya ajan adı tek başına otorite değildir."],
  ["04", "Doğrula ve teslim et", "Kabul kontrolleri, kanıt ve sınırlandırılmış kurtarma sonucun teslime hazır olup olmadığını belirler."],
] as const;

export default function Page(){ return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">ILAIOS Core</div><h1>Her yönetilen yürütmenin çevresinde tek kontrol otoritesi.</h1><p className="lead">Core; istenen sonucu izinler, sınırlandırılmış yürütme, doğrulama, kanıt ve kurtarmayla bağlar. Sistem otoritesi modele, ajana veya sağlayıcıya devredilmez.</p><div className="actions"><Link className="button" href="/tr/capabilities">Yetenekleri keşfet</Link><Link className="button secondary" href="/tr/architecture">Mimariyi incele</Link></div></section>
  <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">Kontrollü yol</div><h2>Hedeften kabul edilmiş sonuca.</h2></div></div><div className="audience-process">{flow.map(([n,title,text])=><article key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></article>)}</div></div></section>
  <section className="section surface-section"><div className="shell audience-focus"><div><span className="micro-label">Core ilkesi</span><h2>Yürütme kaynakları değişebilir. Otorite değişmez.</h2></div><div className="audience-outcome-list"><article><span>01</span><div><strong>Tek kontrol sınırı</strong><p>Kimlik, politika, onaylar ve izin verilen işlemler açık ve merkezi kalır.</p></div></article><article><span>02</span><div><strong>Sınırlandırılmış yürütme</strong><p>Ajanlar, skill'ler, araçlar ve sağlayıcılar yalnız iş için verilen kapsam içinde çalışır.</p></div></article><article><span>03</span><div><strong>Bağımsız kabul</strong><p>Doğrulama ve gerekli onaylar üretilen işin ilerleyip ilerleyemeyeceğini belirler.</p></div></article><article><span>04</span><div><strong>Kanıt ve kurtarma</strong><p>Önemli durum, kaynak kökeni ve hata yönetimi iş başarılı olduğunda da başarısız olduğunda da incelenebilir kalır.</p></div></article></div></div></section>
</>; }
