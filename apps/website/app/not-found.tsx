"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function NotFound() {
  const pathname = usePathname();
  const isTr = pathname === "/tr" || pathname.startsWith("/tr/");

  return (
    <div className="shell prose">
      <div className="eyebrow">404</div>
      <h1>{isTr ? "Sayfa bulunamadı." : "Page not found."}</h1>
      <p>{isTr ? "İstediğiniz sayfa mevcut değil veya taşınmış olabilir." : "The page you requested does not exist or may have moved."}</p>
      <Link className="button" href={isTr ? "/tr" : "/"}>{isTr ? "Ana sayfaya dön" : "Return home"}</Link>
    </div>
  );
}
