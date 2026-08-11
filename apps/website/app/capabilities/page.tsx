import type { Metadata } from "next";
import ProductDeepDive from "../ProductDeepDive";
export const metadata: Metadata = { title: "Capabilities", description: "Explore the major ILAIOS capability families for governed automation, software, web, media, research, intelligence and security.", alternates: { canonical: "/capabilities", languages: { en: "/capabilities", tr: "/tr/capabilities", "x-default": "/capabilities" } } };
export default function Page(){ return <ProductDeepDive locale="en" mode="capabilities" />; }
