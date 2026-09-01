import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata={title:"Resources",description:"Read ILAIOS engineering perspectives on deterministic execution, agent security, control-plane authority, validation, and governed automation.",alternates:{canonical:"/resources",languages:{en:"/resources",tr:"/tr/resources","x-default":"/resources"}}};

const insights=[
  ["Architecture", "Deterministic execution vs. AI agents", "When rules and checks can reliably solve a task, deterministic execution reduces ambiguity. AI agents add value inside explicit boundaries.", "/resources/deterministic-execution-vs-ai-agents"],
  ["Security", "AI agent security & governance", "Why identity, least authority, approvals, validation, audit and evidence matter more than prompt instructions alone.", "/resources/agent-security-and-governance"],
  ["Systems", "Control-plane agent architecture", "Why policy, authorization, durable state, validation and audit authority stay outside clients and model outputs.", "/resources/control-plane-agent-architecture"],
] as const;

export default function Page(){return <>
  <section className="shell page-hero compact-page-hero"><div className="eyebrow">Resources</div><h1>Engineering perspectives behind ILAIOS.</h1><p className="lead">Articles on product architecture, security and governed automation. Resources explains the thinking; Docs carries the technical reference.</p></section>
  <section className="section"><div className="shell"><div className="compact-heading-row"><div><div className="eyebrow">Latest perspectives</div><h2>Readable technical context without turning the page into documentation.</h2></div></div><div className="detail-directory">{insights.map(([kind,title,text,href])=><Link href={href} key={href}><span>{kind}</span><strong>{title}</strong><i>→</i><p>{text}</p></Link>)}</div></div></section>
  <section className="section compact-section"><div className="shell actions"><Link className="text-link" href="/updates">Development updates →</Link><Link className="text-link" href="/docs">Technical documentation →</Link><Link className="text-link" href="/architecture">Architecture →</Link></div></section>
</>}
