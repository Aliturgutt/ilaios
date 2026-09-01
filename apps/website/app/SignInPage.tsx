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
  { id: "google", mark: "G", href: `${APP_ORIGIN}/auth/google/start` },
  { id: "microsoft", mark: "M", href: `${APP_ORIGIN}/auth/microsoft/start` },
  { id: "github", mark: "GH", href: `${APP_ORIGIN}/auth/github/start` },
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
                <span className={styles.providerMark} aria-hidden="true">{provider.mark}</span>
                <span>{c[provider.id]}</span>
                <span className={styles.arrow} aria-hidden="true">→</span>
              </a>
            ))}
          </div>

          <p className={styles.legal}>{c.legal}</p>
        </div>

        <aside className={styles.assurance} aria-label={locale === "tr" ? "Kimlik güvencesi" : "Identity assurance"}>
          <span className={styles.assuranceIndex}>01</span>
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
