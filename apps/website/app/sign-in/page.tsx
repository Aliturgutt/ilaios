import type { Metadata } from "next";
import SignInPage from "../SignInPage";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Securely continue to ILAIOS with Google, Microsoft or GitHub.",
  alternates: {
    canonical: "/sign-in",
    languages: { en: "/sign-in", tr: "/tr/sign-in", "x-default": "/sign-in" },
  },
  robots: { index: false, follow: false },
};

export default function Page() {
  return <SignInPage locale="en" />;
}
