import type { Metadata } from "next";
import AudiencePage from "../../AudiencePage";
export const metadata: Metadata = { title: "Bireysel Kullanıcılar İçin", description: "ILAIOS'un kişisel hedefleri governed research, web, software, media ve operations workflow'larına nasıl dönüştürdüğünü inceleyin.", alternates: { canonical: "/tr/individuals", languages: { tr: "/tr/individuals", en: "/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <AudiencePage locale="tr" audience="individuals" />; }
