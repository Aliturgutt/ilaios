import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import HomePage from "./HomePage";

export const metadata: Metadata = { title: "Governed AI Operating System", description: "ILAIOS turns authenticated goals into governed, validated finished-product workflows with evidence.", alternates: { canonical: "/", languages: { en: "/", tr: "/tr", "x-default": "/tr" } } };

export default async function Page() {
  const preferredLocale = (await cookies()).get("ilaios-locale")?.value;
  if (preferredLocale !== "en") redirect("/tr");
  return <HomePage locale="en" />;
}
