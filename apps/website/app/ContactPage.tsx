import Link from "next/link";
import { motion } from "motion/react";

type Locale = "en" | "tr";

const copy = {
  en: {
    eyebrow: "Contact",
    title: "Contact ILAIOS.",
    lead: "Use the email address that matches your request.",
    topics: [["General & product", "Company, product and partnership enquiries", "contact@ilaios.com"], ["Support", "User and product support", "support@ilaios.com"], ["Privacy", "Privacy and personal-data requests", "privacy@ilaios.com"], ["Security", "Responsible vulnerability reports", "security@ilaios.com"], ["Abuse", "Spam, fraud and misuse reports", "abuse@ilaios.com"]],
  },
  tr: {
    eyebrow: "İletişim",
    title: "ILAIOS ile iletişim.",
    lead: "Talebinize uygun e-posta adresini kullanın.",
    topics: [["Genel ve ürün", "Şirket, ürün ve iş ortaklığı talepleri", "contact@ilaios.com"], ["Destek", "Kullanıcı ve ürün desteği", "support@ilaios.com"], ["Gizlilik", "Gizlilik ve kişisel veri talepleri", "privacy@ilaios.com"], ["Güvenlik", "Sorumlu güvenlik açığı bildirimleri", "security@ilaios.com"], ["Kötüye kullanım", "Spam, dolandırıcılık ve kötüye kullanım bildirimleri", "abuse@ilaios.com"]],
  },
} as const;

export default function ContactPage({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const base = locale === "tr" ? "/tr" : "";
  return <>
    {/* Hero Section with Motion */}
    <section className="shell page-hero compact-page-hero pt-20 pb-20">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
          <h1 className="text-5xl font-bold tracking-tighter mb-4">{c.title}</h1>
        </div>
        <div className="text-base leading-relaxed max-w-2xl mt-4 text-gray-300">{c.lead}</div>
      </motion.div>
    </section>
    <section className="section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="contact-directory grid gap-8">
            {c.topics.map(([title, description, email], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className="border border-gray-600 rounded-lg p-6 hover:bg-gray-700 hover:border-gray-600 hover:text-white transition-all duration-200 hover-lift hover-scale"
              >
                <div className="flex flex-col gap-2">
                  <div className="flex items-start gap-3">
                    <span className="text-xs font-bold text-gray-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <strong className="text-lg font-semibold">{title}</strong>
                    </div>
                  </div>
                  <p className="text-base leading-relaxed text-gray-400">{description}</p>
                  <a href={`mailto:${email}`} className="flex items-center gap-2 text-base font-medium text-white hover:text-white transition-colors duration-200 mt-2 hover-lift hover-scale">{email}</a>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
  </>;
}