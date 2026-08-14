import type { Metadata } from "next";
import PlatformPage from "../PlatformPage";
export const metadata: Metadata = { title: "Platform", description: "Explore the ILAIOS control-oriented platform for authority, bounded execution, validation and evidence.", alternates: { canonical: "/platform", languages: { en: "/platform", tr: "/tr/platform", "x-default": "/platform" } } };
export default function Page() { return <PlatformPage locale="en" />; }
