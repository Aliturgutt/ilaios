import type { Metadata } from "next";
import "./globals.css";
import "./locale.css";
import "./final.css";
import SiteChrome from "./SiteChrome";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ILAIOS", template: "%s | ILAIOS" },
  description: "ILAIOS builds governed infrastructure for intelligent automation and autonomous operations.",
  icons: { icon: [{ url: "/brand/favicon.jpg", type: "image/jpeg" }], shortcut: ["/brand/favicon.jpg"] },
  openGraph: { title: "ILAIOS", description: "Governed infrastructure for intelligent automation and autonomous operations.", url: siteUrl, siteName: "ILAIOS", images: [{ url: "/brand/social-preview.jpg", width: 1280, height: 640, alt: "ILAIOS" }], type: "website" },
  twitter: { card: "summary_large_image", title: "ILAIOS", description: "Governed infrastructure for intelligent automation and autonomous operations.", images: ["/brand/social-preview.jpg"] },
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "ILAIOS",
  url: siteUrl,
  logo: `${siteUrl}/brand/logo-horizontal-dark.jpg`,
  description: "Governed infrastructure for intelligent automation and autonomous operations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }} /><SiteChrome>{children}</SiteChrome></body></html>;
}
