"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import ThemeToggle from "./ThemeToggle";

type NavLink = readonly [label: string, href: string];
type FooterGroup = { heading: string; links: readonly NavLink[] };

const enPrimary = [["Platform", "/platform"], ["Factories", "/factories"], ["Capabilities", "/capabilities"], ["Security", "/security"]] as const;
const trPrimary = [["Platform", "/tr/platform"], ["Üretim", "/tr/factories"], ["Yetenekler", "/tr/capabilities"], ["Güvenlik", "/tr/security"]] as const;
const enExplore = [["Solutions", "/solutions"], ["For Enterprises", "/enterprise"], ["For Individuals", "/individuals"], ["How It Works", "/how-it-works"], ["Use ILAIOS", "/use-ilaios"], ["ILAIOS Core", "/core"], ["Trust Center", "/trust"], ["Architecture", "/architecture"], ["Documentation", "/docs"], ["Resources", "/resources"], ["About", "/about"]] as const;
const trExplore = [["Çözümler", "/tr/solutions"], ["Kurumlar İçin", "/tr/enterprise"], ["Bireysel Kullanıcılar", "/tr/individuals"], ["Nasıl Çalışır", "/tr/how-it-works"], ["ILAIOS'u Kullan", "/tr/use-ilaios"], ["ILAIOS Core", "/tr/core"], ["Güven Merkezi", "/tr/trust"], ["Mimari", "/tr/architecture"], ["Dokümantasyon", "/tr/docs"], ["Kaynaklar", "/tr/resources"], ["Hakkımızda", "/tr/about"]] as const;

function counterpart(pathname: string, isTr: boolean) {
  if (isTr) {
    const next = pathname.replace(/^\/tr(?=\/|$)/, "");
    return next || "/";
  }
  return pathname === "/" ? "/tr" : `/tr${pathname}`;
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

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
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
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("menu-open");
    };
  }, [open]);

  const product: readonly NavLink[] = isTr
    ? [["Platform", "/tr/platform"], ["Üretim", "/tr/factories"], ["Yetenekler", "/tr/capabilities"], ["Nasıl Çalışır", "/tr/how-it-works"]]
    : [["Platform", "/platform"], ["Factories", "/factories"], ["Capabilities", "/capabilities"], ["How It Works", "/how-it-works"]];
  const useLinks: readonly NavLink[] = isTr
    ? [["ILAIOS'u Kullan", "/tr/use-ilaios"], ["Kurumlar", "/tr/enterprise"], ["Bireysel", "/tr/individuals"], ["Çözümler", "/tr/solutions"]]
    : [["Use ILAIOS", "/use-ilaios"], ["Enterprises", "/enterprise"], ["Individuals", "/individuals"], ["Solutions", "/solutions"]];
  const resources: readonly NavLink[] = isTr
    ? [["Mimari", "/tr/architecture"], ["Dokümantasyon", "/tr/docs"], ["Kaynaklar", "/tr/resources"], ["ILAIOS Core", "/tr/core"]]
    : [["Architecture", "/architecture"], ["Documentation", "/docs"], ["Resources", "/resources"], ["ILAIOS Core", "/core"]];
  const trust: readonly NavLink[] = isTr
    ? [["Güvenlik", "/tr/security"], ["Güven Merkezi", "/tr/trust"], ["Gizlilik", "/tr/privacy"]]
    : [["Security", "/security"], ["Trust Center", "/trust"], ["Privacy", "/privacy"]];
  const company: readonly NavLink[] = isTr
    ? [["Hakkımızda", "/tr/about"], ["İletişim", "/tr/contact"], ["Koşullar", "/tr/terms"]]
    : [["About", "/about"], ["Contact", "/contact"], ["Terms", "/terms"]];
  const footerGroups: readonly FooterGroup[] = [
    { heading: isTr ? "Ürün" : "Product", links: product },
    { heading: isTr ? "Kullanım" : "Use", links: useLinks },
    { heading: isTr ? "Kaynaklar" : "Resources", links: resources },
    { heading: isTr ? "Güven" : "Trust", links: trust },
    { heading: isTr ? "Şirket" : "Company", links: company },
  ];

  return <>
    <a className="skip-link" href="#main-content" lang={lang}>{isTr ? "Ana içeriğe geç" : "Skip to main content"}</a>
    <header className="site-header" lang={lang}>
      <div className="shell nav">
        <Link className="brand" href={isTr ? "/tr" : "/"} aria-label={isTr ? "ILAIOS ana sayfa" : "ILAIOS home"} onClick={() => setOpen(false)}>
          <Image className="brand-logo brand-logo-dark" src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} sizes="144px" priority unoptimized />
          <Image className="brand-logo brand-logo-light" src="/brand/logo-horizontal-light.jpg" alt="ILAIOS" width={2400} height={800} sizes="144px" priority unoptimized />
        </Link>
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="site-navigation" aria-label={open ? (isTr ? "Menüyü kapat" : "Close menu") : (isTr ? "Menüyü aç" : "Open menu")} onClick={() => setOpen(value => !value)}><span>{open ? (isTr ? "Kapat" : "Close") : (isTr ? "Menü" : "Menu")}</span><i aria-hidden="true" /></button>
        <nav id="site-navigation" className={`nav-panel ${open ? "is-open" : ""}`} aria-label={isTr ? "Ana menü" : "Primary navigation"}>
          <div className="nav-primary">{primary.map(([label, href]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined} onClick={() => setOpen(false)}>{label}</Link>)}</div>
          <div className="nav-utility"><details className="explore-menu"><summary className={exploreActive ? "is-active" : undefined}>{isTr ? "Keşfet" : "Explore"}</summary><div className="explore-menu-panel">{explore.map(([label, href]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined} onClick={() => setOpen(false)}>{label}</Link>)}</div></details><Link href={isTr ? "/tr/contact" : "/contact"} aria-current={active(isTr ? "/tr/contact" : "/contact") ? "page" : undefined} onClick={() => setOpen(false)}>{isTr ? "İletişim" : "Contact"}</Link><ThemeToggle locale={lang} /><span className="language-switch" aria-label={isTr ? "Dil seçimi" : "Language selection"}>{isTr ? <><Link href={switchHref} hrefLang="en" lang="en" onClick={() => setOpen(false)}>EN</Link><strong aria-current="true">TR</strong></> : <><strong aria-current="true">EN</strong><Link href={switchHref} hrefLang="tr" lang="tr" onClick={() => setOpen(false)}>TR</Link></>}</span></div>
        </nav>
      </div>
    </header>
    <main id="main-content" lang={lang} tabIndex={-1}>{children}</main>
    <footer className="site-footer" lang={lang}>
      <div className="shell footer-main">
        <div className="footer-brand"><strong>ILAIOS</strong><p>{isTr ? "Kontrollü ve doğrulanabilir dijital sonuçlar için yönetilen yapay zekâ işletim sistemi." : "A governed AI operating system for controlled, verifiable finished digital outcomes."}</p><a href="mailto:contact@ilaios.com">contact@ilaios.com</a><div className="footer-social"><a href="https://www.linkedin.com/company/ilaios/" target="_blank" rel="noreferrer">LinkedIn</a><a href="https://x.com/ilaios" target="_blank" rel="noreferrer">X · @ilaios</a></div></div>
        <div className="footer-nav-grid">{footerGroups.map(group => <div key={group.heading}><strong>{group.heading}</strong>{group.links.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}</div>)}</div>
      </div>
      <div className="shell footer-row"><span>© 2026 ILAIOS</span><span>{isTr ? "Kontrollü yürütme · doğrulanmış sonuç" : "Governed execution · verified outcome"}</span><Link href={switchHref}>{isTr ? "English" : "Türkçe"}</Link></div>
    </footer>
  </>;
}
