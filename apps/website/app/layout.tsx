import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import "./locale.css";
import "./final.css";
import "./ux-refresh.css";
import "./professional-final.css";
import "./website-final.css";
import "./adaptive-native.css";
import "./adaptive-structures.css";
import "./mobile-redteam.css";
import "./canonical-detail.css";
import "./visual-redteam-fixes.css";
import "./brand-palette.css";
import "./live-density-fixes.css";
import "./final-interaction-redteam.css";
import "./site-v2-finalization.css";
import SiteChrome from "./SiteChrome";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";
const organizationId = `${siteUrl}/#organization`;
const websiteId = `${siteUrl}/#website`;
const founderId = `${siteUrl}/about#founder`;
const productDescription = "ILAIOS is a Governed AI Operating System with native finished-product factories for controlled, verifiable digital work.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ILAIOS — Governed AI Operating System", template: "%s | ILAIOS" },
  description: productDescription,
  keywords: ["ILAIOS", "Ali Turgut", "Governed AI Operating System", "finished-product factories", "intelligent automation", "AI infrastructure", "governed automation"],
  authors: [{ name: "ILAIOS", url: siteUrl }],
  creator: "ILAIOS",
  publisher: "ILAIOS",
  icons: { icon: [{ url: "/brand/favicon.jpg", type: "image/jpeg" }], shortcut: ["/brand/favicon.jpg"] },
  openGraph: { title: "ILAIOS — Governed AI Operating System", description: productDescription, url: siteUrl, siteName: "ILAIOS", images: [{ url: "/brand/social-preview.jpg", width: 1280, height: 640, alt: "ILAIOS" }], type: "website" },
  twitter: { card: "summary_large_image", title: "ILAIOS — Governed AI Operating System", description: productDescription, images: ["/brand/social-preview.jpg"] },
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "Organization", "@id": organizationId, name: "ILAIOS", url: siteUrl, logo: { "@type": "ImageObject", url: `${siteUrl}/brand/logo-horizontal-dark.jpg` }, description: productDescription, founder: { "@id": founderId }, sameAs: ["https://www.linkedin.com/company/ilaios/", "https://x.com/ilaios"] },
    { "@type": "Person", "@id": founderId, name: "Ali Turgut", url: `${siteUrl}/about#founder`, jobTitle: "Founder", worksFor: { "@id": organizationId }, sameAs: ["https://www.linkedin.com/in/ali-turgut-ilaios/", "https://github.com/Aliturgutt"] },
    { "@type": "WebSite", "@id": websiteId, url: siteUrl, name: "ILAIOS", publisher: { "@id": organizationId }, inLanguage: ["en", "tr"] },
  ],
};

const themeBootstrap = `(() => { try { const key = "ilaios-theme"; const stored = localStorage.getItem(key); const theme = stored === "light" || stored === "dark" ? stored : (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); document.documentElement.dataset.theme = theme; document.documentElement.style.colorScheme = theme; } catch { document.documentElement.dataset.theme = "dark"; } })();`;

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const locale = (await headers()).get("x-ilaios-locale") === "tr" ? "tr" : "en";
  return <html lang={locale} suppressHydrationWarning><body><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }} /><SiteChrome>{children}</SiteChrome></body></html>;
}
