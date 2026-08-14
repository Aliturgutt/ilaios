import type { Metadata } from "next";
import HomePage from "./HomePage";

export const metadata: Metadata = { title: "Governed AI Operating System", description: "ILAIOS turns authenticated goals into governed, validated finished-product workflows with evidence.", alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/" } } };

export default function Page() { return <HomePage locale="en" />; }
