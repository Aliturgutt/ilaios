import type { Metadata } from "next";
import SecurityPage from "../SecurityPage";
export const metadata: Metadata = { title: "Security", description: "Explore the ILAIOS least-authority, approval, validation and evidence security model.", alternates: { canonical: "/security", languages: { en: "/security", tr: "/tr/security", "x-default": "/security" } } };
export default function Page() { return <SecurityPage locale="en" />; }
