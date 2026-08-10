"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const enLinks = [["Platform", "/platform"], ["Security", "/security"], ["About", "/about"], ["Contact", "/contact"]] as const;
const trLinks = [["Platform", "/tr/platform"], ["Güvenlik", "/tr/security"], ["Hakkımızda", "/tr/about"], ["İletişim", "/tr/contact"]] as const;

function counterpart(pathname: string, isTr: boolean) {
  if (isTr) {
    const next = pathname.replace(/^\/tr(?=\/|$)/, "");
    return next || "/";
  }
  return pathname === "/" ? "/tr" : `/tr${pathname}`;
}

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isTr = pathname === "/tr" || pathname.startsWith("/tr/");
  const links = isTr ? trLinks : enLinks;
  const switchHref = counterpart(pathname, isTr);

  return (
    <>
      <header className="site-header">
        <div className="shell nav">
          <Link className="brand" href={isTr ? "/tr" : "/"} aria-label="ILAIOS home">
            <Image src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} priority sizes="168px" />
          </Link>
          <nav className="nav-links" aria-label={isTr ? "Ana menü" : "Primary navigation"}>
            {links.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}
            <span className="language-switch">
              {isTr ? <><Link href={switchHref} hrefLang="en">EN</Link><strong>TR</strong></> : <><strong>EN</strong><Link href={switchHref} hrefLang="tr">TR</Link></>}
            </span>
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="site-footer">
        <div className="shell footer-row">
          <span>© {new Date().getFullYear()} ILAIOS</span>
          <span>
            {isTr ? <><Link href="/tr/privacy">Gizlilik</Link> · <Link href="/tr/terms">Koşullar</Link></> : <><Link href="/privacy">Privacy</Link> · <Link href="/terms">Terms</Link></>}
            {" · "}<Link href={switchHref}>{isTr ? "English" : "Türkçe"}</Link>
          </span>
        </div>
      </footer>
    </>
  );
}
