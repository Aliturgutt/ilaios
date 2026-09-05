"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

type NavLink = readonly [label: string, href: string];
type FooterGroup = { heading: string; links: readonly NavLink[] };

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
  const switchHref = counterpart(pathname, isTr);
  const lang = isTr ? "tr" : "en";

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

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
    <header className="site-header site-header-minimal" lang={lang}>
      <div className="shell nav nav-minimal">
        <Link className="brand" href={isTr ? "/tr" : "/"} aria-label={isTr ? "ILAIOS ana sayfa" : "ILAIOS home"}>
          <Image className="brand-logo brand-logo-dark" src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} sizes="144px" priority unoptimized />
          <Image className="brand-logo brand-logo-light" src="/brand/logo-horizontal-light.jpg" alt="ILAIOS" width={2400} height={800} sizes="144px" priority unoptimized />
        </Link>
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
