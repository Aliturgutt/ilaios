import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Documentation",
  description: "Navigate the public ILAIOS architecture, security, Core, execution, evidence, API and recovery documentation model.",
  alternates: { canonical: "/docs", languages: { en: "/docs", tr: "/tr/docs", "x-default": "/docs" } },
};

const docs = [
  ["Architecture", "System boundaries, control authority and the relationship between clients, execution and evidence.", "/architecture"],
  ["Security", "Permission boundaries, approval gates, least-authority execution and fail-closed controls.", "/security"],
  ["Core", "The single control authority, bounded execution, validation, evidence and recovery model.", "/core"],
  ["Execution", "How admitted work moves through controlled execution without turning a client, model or agent into authority.", "/platform/execution"],
  ["Evidence", "How validation, provenance and reviewable records remain attached to consequential results.", "/platform/evidence"],
  ["API", "Public API references will appear here only when the corresponding contracts are stable and verified.", null],
  ["Recovery", "Public recovery runbooks will be published only when release-specific procedures are verified for the relevant surface.", null],
] as const;

const placeholderCardStyle = {
  minHeight: "116px",
  padding: "20px",
  border: "1px solid var(--line)",
  borderRadius: "var(--v2-radius)",
  background: "transparent",
  boxSizing: "border-box",
} as const;

export default function Page() {
  return <>
    <section className="shell page-hero compact-page-hero">
      <div className="eyebrow">Documentation</div>
      <h1>Technical documentation without turning the product site into a manual.</h1>
      <p className="lead">Use this hub to move directly into the public technical layer. Product pages explain outcomes; documentation explains the control, execution and evidence model behind them.</p>
    </section>
    <section className="section">
      <div className="shell">
        <div className="detail-directory">
          {docs.map(([title, text, href]) => href ? (
            <Link className="dark-surface" href={href} key={title}><span>{title}</span><strong>{text}</strong><i>→</i></Link>
          ) : (
            <article style={placeholderCardStyle} key={title}><div className="eyebrow">{title}</div><p>{text}</p></article>
          ))}
        </div>
      </div>
    </section>
  </>;
}
