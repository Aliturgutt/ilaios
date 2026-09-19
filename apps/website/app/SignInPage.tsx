import Image from "next/image";
import styles from "./SignInPage.module.css";
import { motion } from "motion/react";

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
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
    >
      <section className={styles.page} aria-labelledby="signin-title">
        <div className={styles.frame}>
          <div className={styles.copy}>
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
            >
              <div className={styles.brandLockup} aria-label="ILAIOS">
                <Image
                  className={`${styles.brandLogo} ${styles.brandLogoLight}`}
                  src="/brand/logo-horizontal-light.jpg"
                  alt=""
                  width={2400}
                  height={800}
                  sizes="(max-width: 760px) 100vw, 190px"
                  priority
                  unoptimized
                />
                <Image
                  className={`${styles.brandLogo} ${styles.brandLogoDark}`}
                  src="/brand/logo-horizontal-dark.jpg"
                  alt=""
                  width={2400}
                  height={800}
                  sizes="(max-width: 760px) 100vw, 190px"
                  priority
                  unoptimized
                />
              </div>
              <div className="eyebrow">{c.eyebrow}</div>
              <h1 id="signin-title" className={styles.title}>{c.title}</h1>
              <p className={styles.lead}>{c.lead}</p>
            </motion.div>

            <motion.div
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
            >
              <div className={styles.providers} aria-label={locale === "tr" ? "Giriş sağlayıcıları" : "Sign-in providers"}>
                {providers.map((provider, index) => (
                  <motion.a
                    key={provider.id}
                    initial={{ x: -10, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                    className={`${styles.provider} hover-lift hover-scale`}
                    href={provider.href}
                    rel="nofollow"
                    data-provider={provider.id}
                  >
                    <span className={styles.providerMark} aria-hidden="true">{provider.mark}</span>
                    <span>{c[provider.id]}</span>
                    <span className={styles.arrow} aria-hidden="true">→</span>
                  </motion.a>
                ))}
              </div>

              <p className={styles.legal}>{c.legal}</p>
            </motion.div>
          </div>

          <motion.div
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
          >
            <aside className={styles.assurance} aria-label={locale === "tr" ? "Kimlik güvencesi" : "Identity assurance"}>
              <span className={styles.assuranceIndex}>01</span>
              <div>
                <strong>{c.noteTitle}</strong>
                <p>{c.note}</p>
              </div>
              <div className={styles.securityLine}>{c.security}</div>
            </aside>
          </motion.div>
        </div>
      </section>
    </motion.div>
  );
}
