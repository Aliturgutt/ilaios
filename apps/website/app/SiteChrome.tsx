"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import ThemeToggle from "./ThemeToggle";

type NavLink = readonly [label: string, href: string];
type FooterGroup = { heading: string; links: readonly NavLink[] };

const APP_ORIGIN = "https://app.ilaios.com";
const enPrimary = [["Platform", "/platform"], ["Factories", "/factories"], ["Capabilities", "/capabilities"], ["Security", "/security"]] as const;
const trPrimary = [["Platform", "/tr/platform"], ["Üretim", "/tr/factories"], ["Yetenekler", "/tr/capabilities"], ["Güvenlik", "/tr/security"]] as const;
const enExplore = [["Solutions", "/solutions"], ["For Enterprises", "/enterprise"], ["For Individuals", "/individuals"], ["How It Works", "/how-it-works"], ["Use ILAIOS", "/use-ilaios"], ["ILAIOS Core", "/core"], ["Trust Center", "/trust"], ["Architecture", "/architecture"], ["Documentation", "/docs"], ["Resources", "/resources"], ["About", "/about"], ["Contact", "/contact"]] as const;
const trExplore = [["Çözümler", "/tr/solutions"], ["Kurumlar İçin", "/tr/enterprise"], ["Bireysel Kullanıcılar", "/tr/individuals"], ["Nasıl Çalışır", "/tr/how-it-works"], ["ILAIOS'u Kullan", "/tr/use-ilaios"], ["ILAIOS Core", "/tr/core"], ["Güven Merkezi", "/tr/trust"], ["Mimari", "/tr/architecture"], ["Dokümantasyon", "/tr/docs"], ["Kaynaklar", "/tr/resources"], ["Hakkımızda", "/tr/about"], ["İletişim", "/tr/contact"]] as const;

function counterpart(pathname: string, isTr: boolean) {
  if (isTr) {
    const next = pathname.replace(/^\/tr(?=\/|$)/, "");
    return next || "/?lang=en";
  }
  return pathname === "/" ? "/tr" : `/tr${pathname}`;
}

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [exploreOpen, setExploreOpen] = useState(false);
  const headerRef = useRef<HTMLElement>(null);
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
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        setExploreOpen(false);
        requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(".menu-toggle")?.focus());
      }
    };
    const onPointerDown = (event: PointerEvent) => {
      if (!(event.target instanceof Node)) return;
      const header = headerRef.current;
      if (exploreOpen && (!header || !header.contains(event.target))) {
        setExploreOpen(false);
      }
      if (open && header && !header.contains(event.target)) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
      document.body.classList.remove("menu-open");
    };
  }, [open, exploreOpen]);

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
    <a className="skip-link text-gray-400 hover:text-gray-300" href="#main-content" lang={lang}>{isTr ? "Ana içeriğe geç" : "Skip to main content"}</a>
    <header ref={headerRef} className="site-header bg-gray-900 border-b border-gray-700" lang={lang}>
      <div className="shell nav px-6 py-8">
        <Link className="brand flex items-center space-x-3 mb-6" href={isTr ? "/tr" : "/?lang=en"} aria-label={isTr ? "ILAIOS ana sayfa" : "ILAIOS home"} onClick={() => setOpen(false)}>
          <Image className="brand-logo brand-logo-dark" src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} sizes="(max-width: 760px) 100vw, 144px" priority unoptimized style={{ mixBlendMode: "lighten" }} />
          <Image className="brand-logo brand-logo-light" src="/brand/logo-horizontal-light.jpg" alt="ILAIOS" width={2400} height={800} sizes="(max-width: 760px) 100vw, 144px" priority unoptimized />
          <span className="text-xl font-bold tracking-tighter text-white hover-scale">ILAIOS</span>
        </Link>
        <button className="menu-toggle p-2 rounded-md hover:bg-gray-800 hover:text-white transition-colors duration-200 hover-lift" type="button" aria-expanded={open} aria-controls="site-navigation" aria-label={open ? (isTr ? "Menüyü kapat" : "Close menu") : (isTr ? "Menüyü aç" : "Open menu")} onClick={() => setOpen(value => !value)}>
          <span className="text-gray-400">{open ? (isTr ? "Kapat" : "Close") : (isTr ? "Menü" : "Menu")}</span>
          <i aria-hidden="true" className="ml-1 text-gray-400" />
        </button>
        <motion.nav
          id="site-navigation"
          initial="closed"
          animate={open ? "open" : "closed"}
          exit="closed"
          variants={{
            closed: { y: -10, opacity: 0 },
            open: { y: 0, opacity: 1, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } },
          }}
          className="nav-panel mt-4"
          aria-label={isTr ? "Ana menü" : "Primary navigation"}
        >
          <div className="nav-primary space-x-4">{primary.map(([label, href]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined} onClick={() => setOpen(false)} className="nav-link flex items-center px-3 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200 hover-lift">{label}</Link>)}</div>
          <div className="nav-utility mt-4 flex items-center space-x-4">
            <div className="explore-menu">
              <motion.div
                onClick={() => setExploreOpen(!exploreOpen)}
                className={`${exploreOpen ? "is-active" : ""} px-3 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200 hover-lift hover-scale`}
              >
                {isTr ? "Keşfet" : "Explore"}
                <span className="ml-1 text-gray-400 transition-transform duration-200" style={{ display: 'inline-block' }}>
                  {exploreOpen ? '▼' : '▶'}
                </span>
              </motion.div>
              <AnimatePresence>
                {exploreOpen && (
                  <motion.ul
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="explore-menu-panel mt-2 space-y-2"
                    transition={{ duration: 0.3 }}
                    variants={{
                      closed: { height: 0, opacity: 0 },
                      open: { height: 'auto', opacity: 1, transition: { duration: 0.3, staggerChildren: 0.1 } }
                    }}
                  >
                    {explore.map(([label, href]) => (
                      <motion.li
                        key={href}
                        className="block px-3 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200 hover-lift"
                        onClick={() => {
                          setOpen(false);
                          setExploreOpen(false);
                        }}
                      >
                        <Link href={href} aria-current={active(href) ? "page" : undefined}>
                          {label}
                        </Link>
                      </motion.li>
                    ))}
                  </motion.ul>
                )}
              </AnimatePresence>
            </div>
            <a href={`${APP_ORIGIN}/?lang=${lang}`} onClick={() => setOpen(false)} className="nav-link app-link px-3 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200">{isTr ? "Uygulama" : "App"}</a>
            <ThemeToggle locale={lang} className="ml-4 px-4 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200 text-lg" />
            <span className="language-switch flex items-center space-x2" aria-label={isTr ? "Dil seçimi" : "Language selection"}>{isTr ? <><Link href={switchHref} hrefLang="en" lang="en" onClick={() => setOpen(false)} className="lang-link px-2 py-1 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200">EN</Link><strong aria-current="true" className="lang-current px-2 py-1 rounded-md bg-gray-800 text-white">TR</strong></> : <><strong aria-current="true" className="lang-current px-2 py-1 rounded-md bg-gray-800 text-white">EN</strong><Link href={switchHref} hrefLang="tr" lang="tr" onClick={() => setOpen(false)} className="lang-link px-2 py-1 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200">TR</Link></>}</span>
          </div>
        </motion.nav>
      </div>
    </header>
    <main id="main-content" lang={lang} tabIndex={-1}>
      <AnimatePresence mode="wait">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } }}
          exit={{ opacity: 0, y: -20, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } }}
          key={pathname}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </main>
    <footer className="site-footer bg-gray-900 border-t border-gray-700" lang={lang}>
      <div className="shell footer-main px-6 py-8">
        <div className="footer-brand mb-6">
          <strong className="text-xl font-bold tracking-tighter text-white">ILAIOS</strong>
          <p className="mt-2 text-base leading-relaxed text-gray-300">{isTr ? "Kontrollü ve doğrulanabilir dijital sonuçlar için yönetilen yapay zekâ işletim sistemi." : "A governed AI operating system for controlled, verifiable finished digital outcomes."}</p>
          <div className="footer-social mt-4 flex items-center space-x-4">
            <a className="text-link text-gray-400 hover:text-gray-300 transition-colors duration-200" href="https://www.linkedin.com/company/ilaios/" target="_blank" rel="noreferrer">LinkedIn</a>
            <a className="text-link text-gray-400 hover:text-gray-300 transition-colors duration-200" href="https://x.com/ilaios" target="_blank" rel="noreferrer">X · @ilaios</a>
          </div>
        </div>
        <div className="footer-nav-grid grid gap-6">
          {footerGroups.map(group => (
            <div key={group.heading}>
              <strong className="footer-heading text-lg font-semibold tracking-tighter mb-2 text-white">{group.heading}</strong>
              <div className="space-y-2">{group.links.map(([label, href]) => <Link className="text-link footer-link block px-3 py-2 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors duration-200" key={href} href={href}>{label}</Link>)}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="shell footer-row px-6 py-4 text-center text-sm">
        <span className="text-gray-500">© 2026 ILAIOS</span>
        <span className="mx-4 text-gray-500">{isTr ? "Kontrollü yürütme · doğrulanmış sonuç" : "Governed execution · verified outcome"}</span>
        <Link className="text-link text-gray-400 hover:text-gray-300 transition-colors duration-200" href={switchHref}>{isTr ? "English" : "Türkçe"}</Link>
      </div>
      <div aria-hidden="true" style={{ height: 24 }} />
    </footer>
  </>;
}