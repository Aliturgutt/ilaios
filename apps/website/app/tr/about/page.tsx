import type { Metadata } from "next";
import AboutPage from "../../AboutPage";
export const metadata: Metadata = { title: "ILAIOS Hakkında", description: "ILAIOS'un bitmiş dijital sonuçlar için geliştirdiği yönetilen işletim modelini ve kurucusu Ali Turgut'u tanıyın.", alternates: { canonical: "/tr/about", languages: { tr: "/tr/about", en: "/about", "x-default": "/about" } } };
export default function Page() { return <AboutPage locale="tr" />; }
