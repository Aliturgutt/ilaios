import type { Metadata } from "next";
import AudiencePage from "../AudiencePage";
export const metadata: Metadata = { title: "For Enterprises", description: "How ILAIOS helps organizations govern automation and native finished-product workflows with explicit authority, validation and evidence.", alternates: { canonical: "/enterprise", languages: { en: "/enterprise", tr: "/tr/enterprise", "x-default": "/enterprise" } } };
export default function Page(){ return <AudiencePage locale="en" audience="enterprise" />; }
