import type { Metadata } from "next";
import ProductDeepDive from "../ProductDeepDive";
export const metadata: Metadata = { title: "For Enterprises", description: "How ILAIOS helps organizations govern automation, software, research, media and security workflows.", alternates: { canonical: "/enterprise", languages: { en: "/enterprise", tr: "/tr/enterprise", "x-default": "/enterprise" } } };
export default function Page(){ return <ProductDeepDive locale="en" mode="enterprise" />; }
