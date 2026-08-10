import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ILAIOS", template: "%s | ILAIOS" },
  description: "ILAIOS builds governed infrastructure for intelligent automation and autonomous operations.",
  icons: {
    icon: [{ url: "/brand/favicon.jpg", type: "image/jpeg" }],
    shortcut: ["/brand/favicon.jpg"],
  },
  openGraph: {
    title: "ILAIOS",
    description: "Governed infrastructure for intelligent automation and autonomous operations.",
    url: siteUrl,
    siteName: "ILAIOS",
    images: [{ url: "/brand/social-preview.jpg", width: 1280, height: 640, alt: "ILAIOS" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ILAIOS",
    description: "Governed infrastructure for intelligent automation and autonomous operations.",
    images: ["/brand/social-preview.jpg"],
  },
};

const links = [
  ["Platform", "/platform"],
  ["Security", "/security"],
  ["About", "/about"],
  ["Contact", "/contact"],
] as const;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="shell nav">
            <Link className="brand" href="/" aria-label="ILAIOS home">
              <Image src="/brand/logo-horizontal-dark.jpg" alt="ILAIOS" width={2400} height={800} priority />
            </Link>
            <nav className="nav-links" aria-label="Primary navigation">
              {links.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="site-footer">
          <div className="shell footer-row">
            <span>© {new Date().getFullYear()} ILAIOS</span>
            <span><Link href="/privacy">Privacy</Link> · <Link href="/terms">Terms</Link></span>
          </div>
        </footer>
      </body>
    </html>
  );
}
