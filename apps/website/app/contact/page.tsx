import type { Metadata } from "next";
import ContactPage from "../ContactPage";
export const metadata: Metadata = { title: "Contact", description: "Official ILAIOS contact channels for company, product, support, privacy, security and abuse reporting.", alternates: { canonical: "/contact", languages: { en: "/contact", tr: "/tr/contact", "x-default": "/contact" } } };
export default function Page() { return <ContactPage locale="en" />; }
