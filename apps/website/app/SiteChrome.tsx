"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const enPrimary = [["Platform", "/platform"], ["Capabilities", "/capabilities"], ["Solutions", "/solutions"], ["Security", "/security"]] as const;
const trPrimary = [["Platform", "/tr/platform"], ["Yetenekler", "/tr/capabilities"], ["Çözümler", "/tr/solutions"], ["Güvenlik", "/tr/security"]] as const;
const enExplore = [["For Enterprises", "/enterprise"], ["For Individuals", "/individuals"], ["How It Works", "/how-it-works"], ["ILAIOS Core", "/core"], ["Trust Center", "/trust"], ["Architecture", "/architecture"], ["Documentation", "/docs"], ["Resources", "/resources"], ["About", "/about"]] as const;
const trExplore = [["Kurumlar İçin", "/tr/enterprise"], ["Bireysel Kullanıcılar", "/tr/individuals"], ["Nasıl Çalışır", "/tr/how-it-works"], ["ILAIOS Core", "/tr/core"], ["Güven Merkezi", "/tr/trust"], ["Mimari", "/tr/architecture"], ["Dokümanlar", "/tr/docs"], ["Kaynaklar", "/tr/resources"], ["Hakkımızda", "/tr/about"]] as const;

function counterpart(pathname: string, isTr: boolean) {
  if (isTr) { const next = pathname.replace(/^\/tr(?=\/|$)/, ""); return next || "/"; }
  return pathname === "/" ? "/tr" : `/tr${pathname}`;
}

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuState, setMenuState] = useState({ pathname, open: false });
  const open = menuState.pathname === pathname && menuState.open;
  const closeMenu = () => setMenuState({ pathname, open: false });
  const toggleMenu = () => setMenuState({ pathname, open: !open });
  const isTr = pathname === "/tr" || pathname.startsWith("/tr/");
  const primary = isTr ? trPrimary : enPrimary;
  const explore = isTr ? trExplore : enExplore;
  const switchHref = counterpart(pathname, isTr);
  const lang = isTr ? "tr" : "en";
  const active = (href: string) => pathname === href || (href !== "/" && href !== "/tr" && pathname.startsWith(`${href}/`));
  const exploreActive = explore.some(([, href]) => active(href));

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  useEffect(() => {
    document.body.classList.toggle("menu-open", open);
    if (!open) return () => document.body.classList.remove("menu-open");
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu();
        requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(".menu-toggle")?.focus());
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => { window.removeEventListener("keydown", onKeyDown); document.body.classList.remove("menu-open"); };
  }, [open]);

  return <>
    <a className="skip-link" href="#main-content" lang={lang}>{isTr ? "Ana içeriğe geç" : "Skip to main content"}</a>
    <header className="site-header" lang={lang}>
      <div className="shell nav">
        <Link className="brand" href={isTr ? "/tr" : "/"} aria-label={isTr ? "ILAIOS ana sayfa" : "ILAIOS home"}><Image src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} sizes="168px" priority /></Link>
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="site-navigation" aria-label={open ? (isTr ? "Menüyü kapat" : "Close menu") : (isTr ? "Menüyü aç" : "Open menu")} onClick={toggleMenu}><span>{open ? (isTr ? "Kapat" : "Close") : (isTr ? "Menü" : "Menu")}</span><i aria-hidden="true" /></button>
        <nav id="site-navigation" className={`nav-panel ${open ? "is-open" : ""}`} aria-label={isTr ? "Ana menü" : "Primary navigation"} onClick={(event) => { if ((event.target as HTMLElement).closest("a")) closeMenu(); }}>
          <div className="nav-primary">{primary.map(([label, href]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined}>{label}</Link>)}</div>
          <div className="nav-utility">
            <details className="explore-menu"><summary className={exploreActive ? "is-active" : undefined}>{isTr ? "Keşfet" : "Explore"}</summary><div className="explore-menu-panel">{explore.map(([label, href]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined}>{label}</Link>)}</div></details>
            <Link href={isTr ? "/tr/contact" : "/contact"} aria-current={active(isTr ? "/tr/contact" : "/contact") ? "page" : undefined}>{isTr ? "İletişim" : "Contact"}</Link>
            <span className="language-switch" aria-label={isTr ? "Dil seçimi" : "Language selection"}>{isTr ? <><Link href={switchHref} hrefLang="en" lang="en">EN</Link><strong aria-current="true">TR</strong></> : <><strong aria-current="true">EN</strong><Link href={switchHref} hrefLang="tr" lang="tr">TR</Link></>}</span>
          </div>
        </nav>
      </div>
    </header>
    <main id="main-content" lang={lang}>{children}</main>
    <footer className="site-footer" lang={lang}>
      <div className="shell footer-grid">
        <div className="footer-brand"><strong>ILAIOS</strong><p>{isTr ? "Kurum ve bireylerin hedeflerini kontrollü, doğrulanabilir ve izlenebilir dijital iş akışlarına dönüştürmek için geliştirilen yapay zekâ ve operasyon platformu." : "An AI and digital operations platform designed to turn organizational and individual goals into governed, verifiable and traceable workflows."}</p><a href="mailto:contact@ilaios.com">contact@ilaios.com</a></div>
        <div><strong>{isTr ? "Ürün" : "Product"}</strong><Link href={isTr ? "/tr/platform" : "/platform"}>Platform</Link><Link href={isTr ? "/tr/capabilities" : "/capabilities"}>{isTr ? "Yetenekler" : "Capabilities"}</Link><Link href={isTr ? "/tr/how-it-works" : "/how-it-works"}>{isTr ? "Nasıl Çalışır" : "How It Works"}</Link><Link href={isTr ? "/tr/core" : "/core"}>ILAIOS Core</Link><Link href={isTr ? "/tr/architecture" : "/architecture"}>{isTr ? "Mimari" : "Architecture"}</Link></div>
        <div><strong>{isTr ? "Kullanım" : "Use"}</strong><Link href={isTr ? "/tr/enterprise" : "/enterprise"}>{isTr ? "Kurumlar" : "Enterprises"}</Link><Link href={isTr ? "/tr/individuals" : "/individuals"}>{isTr ? "Bireysel" : "Individuals"}</Link><Link href={isTr ? "/tr/solutions" : "/solutions"}>{isTr ? "Çözümler" : "Solutions"}</Link></div>
        <div><strong>{isTr ? "Güven ve şirket" : "Trust & company"}</strong><Link href={isTr ? "/tr/security" : "/security"}>{isTr ? "Güvenlik" : "Security"}</Link><Link href={isTr ? "/tr/trust" : "/trust"}>{isTr ? "Güven Merkezi" : "Trust Center"}</Link><Link href={isTr ? "/tr/docs" : "/docs"}>{isTr ? "Dokümanlar" : "Documentation"}</Link><Link href={isTr ? "/tr/about" : "/about"}>{isTr ? "Hakkımızda" : "About"}</Link><Link href={isTr ? "/tr/contact" : "/contact"}>{isTr ? "İletişim" : "Contact"}</Link></div>
      </div>
      <div className="shell footer-row"><span>© {new Date().getFullYear()} ILAIOS</span><span className="footer-contact">{isTr ? <><Link href="/tr/privacy">Gizlilik</Link><span>·</span><Link href="/tr/terms">Koşullar</Link></> : <><Link href="/privacy">Privacy</Link><span>·</span><Link href="/terms">Terms</Link></>}<span>·</span><Link href={switchHref}>{isTr ? "English" : "Türkçe"}</Link></span></div>
    </footer>
  </>;
}
