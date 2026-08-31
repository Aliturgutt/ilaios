import type { Metadata } from "next";
import SignInPage from "../../SignInPage";

export const metadata: Metadata = {
  title: "Giriş yap",
  description: "Google, Microsoft veya GitHub ile ILAIOS'a güvenli şekilde devam et.",
  alternates: {
    canonical: "/tr/sign-in",
    languages: { tr: "/tr/sign-in", en: "/sign-in", "x-default": "/sign-in" },
  },
  robots: { index: false, follow: false },
};

export default function Page() {
  return <SignInPage locale="tr" />;
}
