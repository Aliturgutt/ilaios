import type { Metadata } from "next";
import AudiencePage from "../AudiencePage";
export const metadata: Metadata = { title: "For Individuals", description: "How ILAIOS supports personal outcomes through governed research, web, software, media and operations workflows.", alternates: { canonical: "/individuals", languages: { en: "/individuals", tr: "/tr/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <AudiencePage locale="en" audience="individuals" />; }
