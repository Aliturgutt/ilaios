import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata={title:"Kaynaklar",description:"Deterministik yürütme, ajan güvenliği, control-plane otoritesi, doğrulama ve kontrollü otomasyon hakkında ILAIOS mühendislik yazıları.",alternates:{canonical:"/tr/resources",languages:{en:"/resources",tr:"/tr/resources","x-default":"/resources"}}};

const insights=[
  ["Mimari", "Deterministik yürütme ve yapay zekâ ajanları", "Kurallar ve kontroller bir işi güvenilir biçimde çözebiliyorsa deterministik yürütme belirsizliği azaltır; AI ajanları açık sınırlar içinde değer katar.", "/tr/resources/deterministic-execution-vs-ai-agents"],
  ["Güvenlik", "AI ajan güvenliği ve yönetişim", "Kimlik, minimum yetki, onay, doğrulama, denetim ve kanıtın neden yalnız prompt talimatlarından daha güçlü olduğunu inceler.", "/tr/resources/agent-security-and-governance"],
  ["Sistemler", "Control-plane ajan mimarisi", "Politika, yetkilendirme, kalıcı durum, doğrulama ve denetim otoritesinin neden istemci ve model çıktılarının dışında kaldığını açıklar.", "/tr/resources/control-plane-agent-architecture"],
] as const;

export default function Page(){return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">Kaynaklar</div><h1>ILAIOS'un arkasındaki mühendislik yaklaşımı.</h1><p className="lead">Ürün mimarisi, güvenlik ve kontrollü otomasyon üzerine yazılar. Resources yaklaşımı açıklar; Docs teknik referansı taşır.</p></section>
  <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">Güncel görüşler</div><h2>Sayfayı dokümantasyona dönüştürmeden okunabilir teknik bağlam.</h2></div></div><div className="detail-directory">{insights.map(([kind,title,text,href])=><Link href={href} key={href}><span>{kind}</span><strong>{title}</strong><i>→</i><p>{text}</p></Link>)}</div></div></section>
  <section className="section compact-section"><div className="shell actions"><Link className="text-link" href="/tr/updates">Geliştirme güncellemeleri →</Link><Link className="text-link" href="/tr/docs">Teknik dokümantasyon →</Link><Link className="text-link" href="/tr/architecture">Mimari →</Link></div></section>
</>}
