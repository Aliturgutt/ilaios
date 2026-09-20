import Image from "next/image";
import styles from "./SignInPage.module.css";

type Locale = "en" | "tr";

const APP_ORIGIN = "https://app.ilaios.com";

const copy = {
  en: {
    eyebrow: "Secure account access",
    title: "Continue to ILAIOS",
    lead: "Choose a sign-in provider. Authentication is handled by the ILAIOS app runtime and your provider. This page does not collect passwords.",
    google: "Continue with Google",
    microsoft: "Continue with Microsoft",
    github: "Continue with GitHub",
    noteTitle: "One ILAIOS account",
    note: "Provider linking and recovery are handled by the canonical ILAIOS identity layer. Providers are not treated as separate product accounts after an explicit link is completed.",
    security: "Secure sign-in · Provider OAuth · Canonical session",
    legal: "By continuing, you agree to the applicable ILAIOS Terms and Privacy Policy.",
  },
  tr: {
    eyebrow: "Güvenli hesap erişimi",
    title: "ILAIOS'a devam et",
    lead: "Bir giriş sağlayıcısı seç. Kimlik doğrulama ILAIOS uygulama çalışma zamanı ve sağlayıcın tarafından yürütülür. Bu sayfa parola toplamaz.",
    google: "Google ile devam et",
    microsoft: "Microsoft ile devam et",
    github: "GitHub ile devam et",
    noteTitle: "Tek ILAIOS hesabı",
    note: "Sağlayıcı bağlama ve kurtarma işlemleri kanonik ILAIOS kimlik katmanı tarafından yönetilir. Açık bağlantı tamamlandıktan sonra sağlayıcılar ayrı ürün hesapları olarak ele alınmaz.",
    security: "Güvenli giriş · Sağlayıcı OAuth · Kanonik oturum",
    legal: "Devam ederek geçerli ILAIOS Koşulları ve Gizlilik Politikasını kabul etmiş olursun.",
  },
} as const;

const providers = [
  { id: "google", href: `${APP_ORIGIN}/auth/google/start` },
  { id: "microsoft", href: `${APP_ORIGIN}/auth/microsoft/start` },
  { id: "github", href: `${APP_ORIGIN}/auth/github/start` },
] as const;

export default function SignInPage({ locale }: { locale: Locale }) {
  const c = copy[locale];

  return (
    <section className={styles.page} aria-labelledby="signin-title">
      <div className={styles.frame}>
        <div className={styles.copy}>
          <div className={styles.brandLockup} aria-label="ILAIOS">
            <Image
              className={`${styles.brandLogo} ${styles.brandLogoLight}`}
              src="/brand/logo-horizontal-light.jpg"
              alt=""
              width={2400}
              height={800}
              sizes="190px"
              priority
              unoptimized
            />
            <Image
              className={`${styles.brandLogo} ${styles.brandLogoDark}`}
              src="/brand/logo-horizontal-dark.jpg"
              alt=""
              width={2400}
              height={800}
              sizes="190px"
              priority
              unoptimized
            />
          </div>
          <div className="eyebrow">{c.eyebrow}</div>
          <h1 id="signin-title" className={styles.title}>{c.title}</h1>
          <p className={styles.lead}>{c.lead}</p>

          <div className={styles.providers} aria-label={locale === "tr" ? "Giriş sağlayıcıları" : "Sign-in providers"}>
            {providers.map((provider) => (
              <a
                key={provider.id}
                className={styles.provider}
                href={provider.href}
                rel="nofollow"
                data-provider={provider.id}
              >
                <span className={styles.providerMark} aria-hidden="true">{provider.id === "google" ? <svg viewBox="0 0 24 24" width="24" height="24"><path fill="#4285F4" d="M21.35 12.24c0-.71-.06-1.39-.18-2.05H12v3.87h5.24a4.48 4.48 0 0 1-1.94 2.94v2.45h3.15c1.85-1.7 2.9-4.21 2.9-7.21Z"/><path fill="#34A853" d="M12 21.5c2.64 0 4.86-.87 6.48-2.35l-3.15-2.45c-.87.59-1.99.94-3.33.94-2.56 0-4.73-1.73-5.5-4.06H3.25v2.52A9.5 9.5 0 0 0 12 21.5Z"/><path fill="#FBBC05" d="M6.5 13.58a5.7 5.7 0 0 1 0-3.16V7.9H3.25a9.5 9.5 0 0 0 0 8.2l3.25-2.52Z"/><path fill="#EA4335" d="M12 6.36c1.44 0 2.73.5 3.75 1.47l2.81-2.81A9.1 9.1 0 0 0 12 2.5a9.5 9.5 0 0 0-8.75 5.4l3.25 2.52c.77-2.33 2.94-4.06 5.5-4.06Z"/></svg> : provider.id === "microsoft" ? <svg viewBox="0 0 24 24" width="24" height="24"><path fill="#F25022" d="M1 1h10v10H1z"/><path fill="#7FBA00" d="M13 1h10v10H13z"/><path fill="#00A4EF" d="M1 13h10v10H1z"/><path fill="#FFB900" d="M13 13h10v10H13z"/></svg> : <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.56.1.76-.24.76-.54v-2.08c-3.1.67-3.76-1.32-3.76-1.32-.5-1.27-1.23-1.6-1.23-1.6-1.01-.69.08-.68.08-.68 1.12.08 1.7 1.15 1.7 1.15 1 .1.79 1.9 3.24 1.34.1-.72.39-1.21.71-1.49-2.48-.28-5.09-1.24-5.09-5.49 0-1.21.43-2.2 1.14-2.98-.11-.28-.49-1.41.11-2.94 0 0 .93-.3 3.05 1.14a10.6 10.6 0 0 1 5.55 0c2.12-1.44 3.05-1.14 3.05-1.14.6 1.53.22 2.66.11 2.94.71.78 1.14 1.77 1.14 2.98 0 4.26-2.62 5.21-5.11 5.48.4.35.76 1.02.76 2.06v3.05c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z"/></svg>}</span>
                <span>{c[provider.id]}</span>
              </a>
            ))}
          </div>

          <p className={styles.legal}>{c.legal}</p>
        </div>

        <aside className={styles.assurance} aria-label={locale === "tr" ? "Kimlik güvencesi" : "Identity assurance"}>
          <div>
            <strong>{c.noteTitle}</strong>
            <p>{c.note}</p>
          </div>
          <div className={styles.securityLine}>{c.security}</div>
        </aside>
      </div>
    </section>
  );
}
