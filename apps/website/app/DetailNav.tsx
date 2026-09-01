import Link from "next/link";

type NavItem = { href: string; label: string; title: string };

export default function DetailNav({ ariaLabel, previous, next }: { ariaLabel: string; previous?: NavItem; next?: NavItem }) {
  return <nav className="detail-page-navigation" aria-label={ariaLabel}>
    {previous ? <Link className="detail-nav-link" href={previous.href}><span>{previous.label}</span><strong>{previous.title}</strong></Link> : <span />}
    {next ? <Link className="detail-nav-link next" href={next.href}><span>{next.label}</span><strong>{next.title}</strong></Link> : <span />}
  </nav>;
}
