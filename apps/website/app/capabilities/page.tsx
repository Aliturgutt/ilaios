import type { Metadata } from "next";
import CapabilitiesPage from "../CapabilitiesPage";
export const metadata: Metadata = { title: "Capabilities", description: "Explore canonical ILAIOS platform capabilities separately from finished-product factories.", alternates: { canonical: "/capabilities", languages: { en: "/capabilities", tr: "/tr/capabilities", "x-default": "/capabilities" } } };
export default function Page() { return <CapabilitiesPage locale="en" />; }
