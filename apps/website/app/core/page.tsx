import type { Metadata } from "next";
import ProductDeepDive from "../ProductDeepDive";
export const metadata: Metadata = { title: "ILAIOS Core", description: "Understand the ILAIOS Core control, validation, evidence and recovery model.", alternates: { canonical: "/core", languages: { en: "/core", tr: "/tr/core", "x-default": "/core" } } };
export default function Page(){ return <ProductDeepDive locale="en" mode="core" />; }
