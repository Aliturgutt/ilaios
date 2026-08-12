import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Ajan Organizasyonu",
  description: "ILAIOS uzman ajan kimliklerinin, ekiplerin, yeteneklerin, izinlerin, bağımsız doğrulamanın ve bounded runtime execution sınırlarının nasıl yönetildiği.",
  alternates: { canonical: "/tr/agents", languages: { en: "/agents", tr: "/tr/agents", "x-default": "/agents" } },
};

const teams = [
  ["Core", "Orchestrator, Planner, Supervisor, Policy ve CostResource planlama, yönetişim ve kaynak sınırlarını koordine eder."],
  ["Engineering", "Mimari, core, frontend, backend, integration, test, code review, runtime QA, release assessment ve recovery rolleri."],
  ["Security", "Savunma odaklı coordinator, code, web/API, supply-chain, infrastructure ve bağımsız verification rolleri."],
  ["Web", "Kontrollü web workflow'ları için UX, visual, asset, content, SEO ve browser-QA rolleri."],
  ["Media", "Story, scene direction, media generation, voice/audio, editing, QA, social metadata ve publishing rolleri."],
  ["Intelligence", "Research, fact-check, data analysis ve knowledge rolleri."],
  ["Operations", "Automation, analytics, monitoring, recovery, provider watching ve benchmark rolleri."],
  ["Meta", "Independent verification ve kontrollü self-development coordination rolleri."],
] as const;

const rules = [
  ["Kalıcı machine identity", "Orchestration; kalıcı ilaios.agent.* machine ID'lerine, capability contract'larına ve izinlere bağlanır. İnsan-okunur alias'lar yalnız sunum metadata'sıdır."],
  ["İsim yetki değildir", "Bir ajan adı tek başına izin vermez. Caller/target sınırları, execution grant, policy ve security kontrolleri neyin çalışabileceğini belirler."],
  ["Verifier ayrımı", "Hiçbir ajan kendi çıktısını bağımsız doğrulayamaz; implementation rolleri kendi çıktısını VERIFIED veya PRODUCTION'a yükseltemez."],
  ["Readiness kanıtla belirlenir", "REGISTERED, yönetilen kimlik ve manifest bulunduğu anlamına gelir. Uzman executor readiness için ayrı bounded runtime ve E2E evidence gerekir."],
] as const;

export default function Page() { return <>
  <section className="shell page-hero"><div className="eyebrow">ILAIOS ajan organizasyonu</div><h1>Kalıcı kimlikler, açık izinler ve bağımsız doğrulama arkasındaki uzman roller.</h1><p className="lead">ILAIOS çok ekipli, yönetilen bir ajan organizasyonu kullanır; ancak orchestration bir isim veya persona'ya bağlı değildir. Machine ID, capability contract, permissions, allowed callers/targets, escalation path ve verifier identity otorite olarak kalır.</p></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Ekipler</div><h2>Uzmanlaşma kontrolsüz özerklikle değil, sorumlulukla düzenlenir.</h2></div><p className="muted">Repository bu ekiplerdeki named specialist kayıtlarını yönetir. Registration kimlik/yönetişim metadata'sını kanıtlar; her uzmanın doğrulanmış provider-backed executor'a sahip olduğunu tek başına iddia etmez.</p></div><div className="grid two-up">{teams.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
  <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">Doğrulanmış runtime bridge</div><h2>Bounded bir named-agent yolu artık end-to-end execution evidence'a sahip.</h2></div><p className="muted">Repository testleri, kanonik bir security producer'ın permission firewall üzerinden kabul edilmesini, mevcut governed runtime içinde deterministic-first yürütülmesini, route evidence'ın kalıcı tutulmasını ve bağımsız verification'ın farklı bir kanonik verifier'a devredilmesini doğrular. Alias hedefler ve security scan geçmemiş invocation'lar runtime'a ulaşmadan fail-closed olur. Bu, ilgili bounded yol için E2E kanıttır; kayıtlı tüm ajanların genel kullanıma açık olduğu anlamına gelmez.</p></div><div className="grid two-up">{rules.map(([title,text]) => <article className="card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div><div className="actions"><Link className="button" href="/tr/how-it-works">ILAIOS nasıl çalışır</Link><Link className="button secondary" href="/tr/security/permissions">İzin modeli</Link><Link className="text-link" href="/tr/platform/evidence">Evidence modeli →</Link></div></div></section>
</>; }
