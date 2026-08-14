import type { Metadata } from "next";
import AudiencePage from "../../AudiencePage";
export const metadata: Metadata = { title: "Bireysel Kullanıcılar İçin", description: "ILAIOS'un bireysel research, web, software, app, media ve operations workflow'larını state ve acceptance görünür kalacak şekilde nasıl yönettiğini inceleyin.", alternates: { canonical: "/tr/individuals", languages: { tr: "/tr/individuals", en: "/individuals", "x-default": "/individuals" } } };
export default function Page(){ return <AudiencePage locale="tr" audience="individuals" />; }
