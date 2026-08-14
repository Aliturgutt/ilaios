import type { Metadata } from "next";
import AudiencePage from "../AudiencePage";
export const metadata: Metadata = { title: "For Individuals", description: "How ILAIOS supports governed personal research, web, software, app, media and operations workflows while keeping state and acceptance visible.", alternates: { canonical: "/individuals", languages: { en: "/individuals", tr: "/tr/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <AudiencePage locale="en" audience="individuals" />; }
