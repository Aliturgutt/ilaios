import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";

export const metadata: Metadata = { title: "Güncellemeler", description: "ILAIOS güncellemeleri kaynaklar sayfasına yönlendirilir.", alternates: { canonical: "/resources", languages: { en: "/resources", tr: "/tr/resources", "x-default": "/resources" } } };

export default function Page() {
  permanentRedirect("/tr/resources");
}
