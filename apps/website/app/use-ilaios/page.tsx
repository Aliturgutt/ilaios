import type { Metadata } from "next";
import UseILAIOSPage from "../UseILAIOSPage";

export const metadata: Metadata = {
  title: "Use ILAIOS",
  description: "Learn what to provide, what ILAIOS can create, how governed execution works, what current factory readiness means, and what evidence accompanies accepted results.",
  alternates: { canonical: "/use-ilaios", languages: { en: "/use-ilaios", tr: "/tr/use-ilaios", "x-default": "/use-ilaios" } },
};

export default function Page() { return <UseILAIOSPage locale="en" />; }
