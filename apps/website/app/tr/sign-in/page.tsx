import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Giriş Yap - ILAIOS",
  description: "ILAIOS Yönetilen Yapay Zeka İşletim Sistemi'ne giriş yapın",
  alternates: {
    canonical: "/tr/sign-in",
    languages: {
      en: "/sign-in",
      tr: "/tr/sign-in",
      'x-default': "/sign-in",
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
