import type { Metadata } from "next";
import WebsiteV2HomeRecovery from "./WebsiteV2HomeRecovery";

export const metadata: Metadata = { title: "Governed AI Operating System", description: "ILAIOS turns authenticated goals into governed, validated finished-product workflows with evidence.", alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/" } } };

export default function Page() { return <WebsiteV2HomeRecovery locale="en" />; }
