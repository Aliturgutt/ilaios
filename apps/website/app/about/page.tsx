import type { Metadata } from "next";
import AboutPage from "../AboutPage";
export const metadata: Metadata = { title: "About", description: "Learn why ILAIOS is building a governed operating system for finished digital outcomes and about founder Ali Turgut.", alternates: { canonical: "/about", languages: { en: "/about", tr: "/tr/about", "x-default": "/about" } } };
export default function Page() { return <AboutPage locale="en" />; }
