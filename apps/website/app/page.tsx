import type { Metadata } from "next";
import { redirect } from "next/navigation";
import HomePage from "./HomePage";

export const metadata: Metadata = { title: "Governed AI Operating System", description: "ILAIOS turns authenticated goals into governed, validated finished-product workflows with evidence.", alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/tr" } } };

export default async function Page({ searchParams }: { searchParams: Promise<{ lang?: string | string[] }> }) {
  const params = await searchParams;
  const lang = Array.isArray(params.lang) ? params.lang[0] : params.lang;
  if (lang !== "en") redirect("/tr");
  return <HomePage locale="en" />;
}
