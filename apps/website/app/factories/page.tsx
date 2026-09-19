import type { Metadata } from "next";
import FactoriesPage from "../FactoriesPage";
export const metadata: Metadata = { title: "ILAIOS Factories", description: "Explore specialized ILAIOS production and operations factories under one governed operating model.", alternates: { canonical: "/factories", languages: { en: "/factories", tr: "/tr/factories", "x-default": "/factories" } } };
export default function Page() { return <FactoriesPage locale="en" />; }
