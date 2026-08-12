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

function LinkedInIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5.3 3.8A2.3 2.3 0 1 1 5.3 8.4 2.3 2.3 0 0 1 5.3 3.8ZM3.4 9.9h3.8v10.7H3.4V9.9Zm6.1 0h3.6v1.5h.1c.5-.9 1.7-1.9 3.6-1.9 3.9 0 4.6 2.5 4.6 5.8v5.3h-3.8v-4.7c0-1.1 0-2.6-1.7-2.6s-1.9 1.2-1.9 2.5v4.8H9.5V9.9Z" /></svg>;
}

function XIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M18.5 3H22l-7.6 8.7L23 21h-6.7l-5.2-6.8L5.2 21H1.7l7.8-8.9L1.2 3H8l4.7 6.2L18.5 3Zm-1.2 16h1.9L7 4.9H5L17.3 19Z" /></svg>;
}

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isTr = pathname === "/tr" || pathname.startsWith("/tr/");
  const primary = isTr ? trPrimary : enPrimary;
  const explore = isTr ? trExplore : enExplore;
  const switchHref = counterpart(pathname, isTr);
  const lang = isTr ? "tr" : "en";
  const active = (href: string) => pathname === href || (href !== "/" && href !== "/tr" && pathname.startsWith(`${href}/`));
  const exploreActive = explore.some(([, href]) => active(href));

  useEffect(() => { document.documentElement.lang = lang; setOpen(false); }, [lang, pathname]);
  useEffect(() => {
    document.body.classList.toggle("menu-open", open);
    if (!open) return () => document.body.classList.remove("menu-open");
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
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
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="site-navigation" aria-label={open ? (isTr ? "Menüyü kapat" : "Close menu") : (isTr ? "Menüyü aç" : "Open menu")} onClick={() => setOpen(value => !value)}><span>{open ? (isTr ? "Kapat" : "Close") : (isTr ? "Menü" : "Menu")}</span><i aria-hidden="true" /></button>
        <nav id="site-navigation" className={`nav-panel ${open ? "is-open" : ""}`} aria-label={isTr ? "Ana menü" : "Primary navigation"}>
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
        <div className="footer-brand">
          <strong>ILAIOS</strong>
          <p>{isTr ? "Kurum ve bireylerin hedeflerini kontrollü, doğrulanabilir ve izlenebilir dijital iş akışlarına dönüştürmek için geliştirilen yapay zekâ ve operasyon platformu." : "An AI and digital operations platform designed to turn organizational and individual goals into governed, verifiable and traceable workflows."}</p>
          <div className="footer-contact-block">
            <a className="footer-email" href="mailto:contact@ilaios.com">contact@ilaios.com</a>
            <div className="footer-socials" aria-label={isTr ? "ILAIOS sosyal medya hesapları" : "ILAIOS social profiles"}>
              <a href="https://www.linkedin.com/company/ilaios/" target="_blank" rel="noreferrer" aria-label={isTr ? "ILAIOS LinkedIn şirket sayfası" : "ILAIOS company on LinkedIn"}><LinkedInIcon /><span>LinkedIn</span></a>
              <a href="https://x.com/ilaios" target="_blank" rel="noreferrer" aria-label={isTr ? "ILAIOS X hesabı" : "ILAIOS on X"}><XIcon /><span>X</span></a>
            </div>
          </div>
        </div>
        <div><strong>{isTr ? "Ürün" : "Product"}</strong><Link href={isTr ? "/tr/platform" : "/platform"}>Platform</Link><Link href={isTr ? "/tr/capabilities" : "/capabilities"}>{isTr ? "Yetenekler" : "Capabilities"}</Link><Link href={isTr ? "/tr/how-it-works" : "/how-it-works"}>{isTr ? "Nasıl Çalışır" : "How It Works"}</Link><Link href={isTr ? "/tr/core" : "/core"}>ILAIOS Core</Link><Link href={isTr ? "/tr/architecture" : "/architecture"}>{isTr ? "Mimari" : "Architecture"}</Link></div>
        <div><strong>{isTr ? "Kullanım" : "Use"}</strong><Link href={isTr ? "/tr/enterprise" : "/enterprise"}>{isTr ? "Kurumlar" : "Enterprises"}</Link><Link href={isTr ? "/tr/individuals" : "/individuals"}>{isTr ? "Bireysel" : "Individuals"}</Link><Link href={isTr ? "/tr/solutions" : "/solutions"}>{isTr ? "Çözümler" : "Solutions"}</Link></div>
        <div><strong>{isTr ? "Güven ve şirket" : "Trust & company"}</strong><Link href={isTr ? "/tr/security" : "/security"}>{isTr ? "Güvenlik" : "Security"}</Link><Link href={isTr ? "/tr/trust" : "/trust"}>{isTr ? "Güven Merkezi" : "Trust Center"}</Link><Link href={isTr ? "/tr/docs" : "/docs"}>{isTr ? "Dokümanlar" : "Documentation"}</Link><Link href={isTr ? "/tr/about" : "/about"}>{isTr ? "Hakkımızda" : "About"}</Link><Link href={isTr ? "/tr/contact" : "/contact"}>{isTr ? "İletişim" : "Contact"}</Link></div>
      </div>
      <div className="shell footer-row"><span>© {new Date().getFullYear()} ILAIOS</span><span className="footer-contact">{isTr ? <><Link href="/tr/privacy">Gizlilik</Link><span>·</span><Link href="/tr/terms">Koşullar</Link></> : <><Link href="/privacy">Privacy</Link><span>·</span><Link href="/terms">Terms</Link></>}<span>·</span><Link href={switchHref}>{isTr ? "English" : "Türkçe"}</Link></span></div>
    </footer>
  </>;
}
