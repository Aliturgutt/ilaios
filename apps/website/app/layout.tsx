import type { Metadata } from "next";
import "./globals.css";
import "./locale.css";
import "./final.css";
import "./ux-refresh.css";
import "./professional-final.css";
import SiteChrome from "./SiteChrome";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";
const organizationId = `${siteUrl}/#organization`;
const websiteId = `${siteUrl}/#website`;

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ILAIOS", template: "%s | ILAIOS" },
  description: "ILAIOS builds governed infrastructure for intelligent automation and autonomous operations.",
  keywords: ["ILAIOS", "intelligent automation", "autonomous operations", "AI infrastructure", "governed automation"],
  alternates: { canonical: siteUrl },
  authors: [{ name: "ILAIOS", url: siteUrl }],
  creator: "ILAIOS",
  publisher: "ILAIOS",
  icons: { icon: [{ url: "/brand/favicon.jpg", type: "image/jpeg" }], shortcut: ["/brand/favicon.jpg"] },
  openGraph: { title: "ILAIOS", description: "Governed infrastructure for intelligent automation and autonomous operations.", url: siteUrl, siteName: "ILAIOS", images: [{ url: "/brand/social-preview.jpg", width: 1280, height: 640, alt: "ILAIOS" }], type: "website" },
  twitter: { card: "summary_large_image", title: "ILAIOS", description: "Governed infrastructure for intelligent automation and autonomous operations.", images: ["/brand/social-preview.jpg"] },
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": organizationId,
      name: "ILAIOS",
      url: siteUrl,
      logo: {
        "@type": "ImageObject",
        url: `${siteUrl}/brand/logo-horizontal-dark.jpg`,
      },
      description: "Governed infrastructure for intelligent automation and autonomous operations.",
    },
    {
      "@type": "WebSite",
      "@id": websiteId,
      url: siteUrl,
      name: "ILAIOS",
      publisher: { "@id": organizationId },
      inLanguage: ["en", "tr"],
    },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }} /><SiteChrome>{children}</SiteChrome></body></html>;
}
