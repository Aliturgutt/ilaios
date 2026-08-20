import type { Metadata } from "next";
import HomePage from "./HomePage";
import SuppliedVisual from "./SuppliedVisual";

export const metadata: Metadata = { title: "Governed AI Operating System", description: "ILAIOS turns authenticated goals into governed, validated finished-product workflows with evidence.", alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/" } } };

export default function Page() { return <><HomePage locale="en" /><section className="section surface-section"><div className="shell"><SuppliedVisual priority light="/website-v2/homepage-light.avif" dark="/website-v2/homepage-dark.avif" alt="ILAIOS governed digital operating platform flow from business goal through one governed Core, shared capabilities, production factories and validation to an evidence-backed outcome." caption="Canonical direction: business work composes shared governed capabilities and specialized production factories without creating a second execution authority." /></div></section></>; }
