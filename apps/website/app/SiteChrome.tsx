"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

const enLinks = [["Platform", "/platform"], ["Solutions", "/solutions"], ["Architecture", "/architecture"], ["Security", "/security"], ["Trust", "/trust"], ["Docs", "/docs"], ["Resources", "/resources"], ["About", "/about"], ["Contact", "/contact"]] as const;
const trLinks = [["Platform", "/tr/platform"], ["Çözümler", "/tr/solutions"], ["Mimari", "/tr/architecture"], ["Güvenlik", "/tr/security"], ["Güven", "/tr/trust"], ["Dokümanlar", "/tr/docs"], ["Kaynaklar", "/tr/resources"], ["Hakkımızda", "/tr/about"], ["İletişim", "/tr/contact"]] as const;

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
  const lang = isTr ? "tr" : "en";

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  return <>
    <a className="skip-link" href="#main-content" lang={lang}>{isTr ? "Ana içeriğe geç" : "Skip to main content"}</a>
    <header className="site-header" lang={lang}><div className="shell nav">
      <Link className="brand" href={isTr ? "/tr" : "/"} aria-label={isTr ? "ILAIOS ana sayfa" : "ILAIOS home"}><Image src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} sizes="168px" /></Link>
      <nav className="nav-links" aria-label={isTr ? "Ana menü" : "Primary navigation"}>{links.map(([label, href]) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}>{label}</Link>)}<span className="language-switch" aria-label={isTr ? "Dil seçimi" : "Language selection"}>{isTr ? <><Link href={switchHref} hrefLang="en" lang="en">EN</Link><strong aria-current="true">TR</strong></> : <><strong aria-current="true">EN</strong><Link href={switchHref} hrefLang="tr" lang="tr">TR</Link></>}</span></nav>
    </div></header>
    <main id="main-content" lang={lang}>{children}</main>
    <footer className="site-footer" lang={lang}>
      <div className="shell footer-trust"><div><strong>ILAIOS</strong><p>{isTr ? "Kontrollü akıllı otomasyon için güvenlik, kanıt ve açık yetki sınırları etrafında geliştirilen teknoloji." : "Technology for governed intelligent automation, built around security, evidence, and explicit authority boundaries."}</p></div><div className="footer-signals"><span>{isTr ? "Aktif geliştirme" : "Active development"}</span><span>{isTr ? "Kanıt odaklı" : "Evidence-first"}</span><span>{isTr ? "Güvenlik odaklı" : "Security-first"}</span></div></div>
      <div className="shell footer-row"><span>© {new Date().getFullYear()} ILAIOS</span><span className="footer-contact"><Link href={isTr ? "/tr/architecture" : "/architecture"}>{isTr ? "Mimari" : "Architecture"}</Link><span>·</span><Link href={isTr ? "/tr/trust" : "/trust"}>{isTr ? "Güven Merkezi" : "Trust Center"}</Link><span>·</span><Link href={isTr ? "/tr/docs" : "/docs"}>{isTr ? "Dokümanlar" : "Docs"}</Link><span>·</span><Link href={isTr ? "/tr/contact" : "/contact"}>{isTr ? "İletişim" : "Contact"}</Link><span>·</span><a href="mailto:contact@ilaios.com">contact@ilaios.com</a><span>·</span>{isTr ? <><Link href="/tr/privacy">Gizlilik</Link><span>·</span><Link href="/tr/terms">Koşullar</Link></> : <><Link href="/privacy">Privacy</Link><span>·</span><Link href="/terms">Terms</Link></>}<span>·</span><Link href={switchHref}>{isTr ? "English" : "Türkçe"}</Link></span></div>
    </footer>
  </>;
}
