import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";

export const metadata: Metadata = { title: "Updates", description: "ILAIOS updates redirect to resources.", alternates: { canonical: "/resources", languages: { en: "/resources", tr: "/tr/resources", "x-default": "/resources" } } };

export default function Page() {
  permanentRedirect("/resources");
}
