import type { Metadata } from "next";
import ProductDeepDive from "../ProductDeepDive";
export const metadata: Metadata = { title: "For Individuals", description: "How ILAIOS supports personal automation, research, software, web and media workflows with governed execution.", alternates: { canonical: "/individuals", languages: { en: "/individuals", tr: "/tr/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <ProductDeepDive locale="en" mode="individuals" />; }
