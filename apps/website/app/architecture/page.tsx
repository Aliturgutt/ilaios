import type { Metadata } from "next";
import ArchitecturePage from "../ArchitecturePage";
export const metadata: Metadata = { title: "Architecture", description: "Understand the ILAIOS control-plane architecture, authority flow, routing, validation and evidence path.", alternates: { canonical: "/architecture", languages: { en: "/architecture", tr: "/tr/architecture", "x-default": "/architecture" } } };
export default function Page() { return <ArchitecturePage locale="en" />; }
