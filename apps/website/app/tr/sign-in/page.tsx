import type { Metadata } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  title: "Giriş Yap - ILAIOS",
  description: "ILAIOS Yönetilen Yapay Zeka İşletim Sistemi'ne giriş yapın",
  alternates: {
    canonical: `${siteUrl}/tr/sign-in`,
    languages: {
      en: `${siteUrl}/sign-in`,
      tr: `${siteUrl}/tr/sign-in`,
      'x-default': `${siteUrl}/sign-in`,
    },
  },
};

export default function SignInPage() {
  return (
    <div>
      <h1>Giriş Yap</h1>
      <p>Giriş sayfası placeholder.</p>
    </div>
  );
}
