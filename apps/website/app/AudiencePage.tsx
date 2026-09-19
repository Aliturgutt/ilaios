'use client';

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";

type Locale = "en" | "tr";
type Audience = "enterprise" | "individuals";

const copy = {
  en: {
    enterprise: {
      eyebrow: "For enterprises",
      title: "Turn complex work into controlled, reviewable outcomes.",
      lead: "ILAIOS is designed for teams that want one place to request work, coordinate production and keep important actions inside explicit organizational controls.",
      focusLabel: "What teams can move forward",
      focusTitle: "Start with the business outcome. Keep governance around the work.",
      outcomes: [["Launch a web experience", "Move from requirements and content through implementation, QA and delivery preparation without operating a separate tool chain."], ["Ship software work", "Structure engineering work around repository context, tests, review and acceptance instead of treating generated code as finished."], ["Produce media", "Coordinate research, script, assets, audio, render and validation as one managed production flow."], ["Research a decision", "Keep sources, claims, uncertainty and review context connected so teams can inspect how an answer was formed."], ["Automate recurring work", "Turn repeatable operational tasks into bounded workflows with visible state and clear handoffs."], ["Review what happened", "Keep material actions and acceptance context inspectable instead of losing them across disconnected tools."]],
      operating: [["01", "Describe the result", "The team states what needs to be finished and the relevant organizational context."], ["02", "Set the boundaries", "Identity, permissions and required approvals determine what the work may use or change."], ["03", "Produce and verify", "The appropriate capabilities perform the admitted work and acceptance checks decide what advances."], ["04", "Deliver with context", "The result is returned with the state and evidence needed for review and follow-up."]],
      primary: "Explore production areas",
      secondary: "See the architecture",
    },
    individuals: {
      eyebrow: "For individuals",
      title: "Ask for the finished result, not a stack of tools to operate.",
      lead: "ILAIOS is designed to help an individual move from an idea or task toward a reviewable result across research, web, software, media and personal workflows.",
      focusLabel: "Outcome first",
      focusTitle: "Spend less time coordinating tools and more time deciding what should be finished.",
      outcomes: [["Research", "Turn a question into structured research with sources, claims and uncertainty that you can review."], ["Website", "Move from a goal and references through structure, design, implementation and QA toward a finished site."], ["Software", "Keep changes connected to repository context, tests and review before treating the work as complete."], ["Application", "Plan and structure application work while broader production capability continues to mature."], ["Video and media", "Coordinate script, assets, audio, render and validation through one production flow."], ["Personal operations", "Prepare and manage repeatable work without silently expanding what the system is allowed to do."]],
      operating: [["01", "Say what you want", "Describe the result instead of choosing internal models, agents or providers."], ["02", "Add the useful context", "References, project context and permissions define what can participate in the work."], ["03", "Let the work run", "The relevant capabilities perform the task inside the allowed boundaries."], ["04", "Review the result", "The outcome and its verification remain visible so you can decide what happens next."]],
      primary: "See what ILAIOS can produce",
      secondary: "See how it works",
    },
  },
  tr: {
    enterprise: {
      eyebrow: "Kurumlar için",
      title: "Karmaşık işleri controllü ve incelenebilir sonuçlara dönüştürün.",
      lead: "ILAIOS; ekiplerin işi tek yerden talep etmesi, üretimi koordine etmesi ve önemli işlemleri açık kurumsal kontroller içinde tutması için tasarlanır.",
      focusLabel: "Ekiplerin ilerletebileceği işler",
      focusTitle: "İş sonucuyla başlayın. Yönetişimi işin çevresinde tutun.",
      outcomes: [["Bir web deneyimi yayınlayın", "Gereksinim ve içerikten geliştirme, QA ve teslim hazırlığına ayrı bir araç zincirinin operatörü olmadan ilerleyin."], ["Yazılım işi teslim edin", "Üretilen kodu bitmiş saymak yerine repository bağlamı, test, inceleme ve kabul etrafında mühendislik işini yapılandırın."], ["Medya üretin", "Araştırma, senaryo, varlıklar, ses, render ve doğrulamayı tek yönetilen üretim akışında koordine edin."], ["Bir kararı araştırın", "Kaynak, iddia, belirsizlik ve inceleme bağnamı bağlı tutarak sonucun nasıl oluştuğını ekipçe görebilin."], ["Tekrarlanan işleri otomatikleştirin", "Operasyonel işleri görünür durum ve açık devir noktaları olan sınırlandırılmış akışlara dönüştürün."], ["Ne olduğunu inceleyin", "Önemli işlemleri ve kabul bağnamı birbirinden kopuk araçlarda kaybetmek yerine incelenebilir tutun."]],
      operating: [["01", "Sonucu tarif edin", "Ekip neyin bitmesi gerektiğini ve gerekli kurumsal bağnamı belirtir."], ["02", "Sınırları belirleyin", "Kimlik, izinler ve gerekli onaylar işin neyi kullanabileceğini veya değiştirebileceğini belirler."], ["03", "Üretin ve doğrulayın", "Uygun yetenekler kabul etmiş işi yapar; kabul kontrolleri neyin ilerleyeceğini belirler."], ["04", "Bağnamıyla teslim alın", "Sonuç, inceleme ve takip için gereken durum ve kanıtla birlikte sunulur."]],
      primary: "Üretim alanlarını keşfet",
      secondary: "Mimariyi incele",
    },
    individuals: {
      eyebrow: "Bireysel kullanıcılar için",
      title: "Araç yığınını değil, bitmiş sonucu isteyin.",
      lead: "ILAIOS; bir fikri veya işi araştırma, web, yazılım, medya ve kişisel iş akışları boyunca incelenebilir bir sonuca taşımaya yardımcı olmak için tasarlanır.",
      focusLabel: "Önce sonuç",
      focusTitle: "Araçları koordine etmeye daha az, neyin bitmesi gerektiğine daha fazla zaman ayırın.",
      outcomes: [["Araştırma", "Bir soruyu kaynakları, iddiaları ve belirsizliği görülebilen yapılandırılmış araştırmaya dönüştürün."], ["Web sitesi", "Hedef ve referanslardan yapı, tasarım, geliştirme ve QA üzerinden bitmiş siteye ilerleyin."], ["Yazılım", "İşi tamamlanmış saymadan önce değişiklikleri repository bağlamı, testler ve incelemeyle bağlı tutun."], ["Uygulama", "Daha geniş production yeteneği gelişmeye devam ederken uygulama işini planlayın ve yapılandırın."], ["Video ve medya", "Senaryo, varlıklar, ses, render ve doğrulamayı tek üretim akışında koordine edin."], ["Kişisel operasyon", "Sistemin yetkisini sessizce genişletmeden tekrarlanan işleri hazırlayın ve yönetin."]],
      operating: [["01", "Ne istediğinizi söyleyin", "İç model, ajan veya sağlayıcı seçmek yerine sonucu tarif edin."], ["02", "Gerekli bağnamı ekleyin", "Referanslar, proje bağnamı ve izinler işe nelerin katılabileceğini belirler."], ["03", "İşi yürütün", "Uygun yetenekler görevi izin verilen sınırnarlarda yapar."], ["04", "Sonucu inceleyin", "Sonuç ve doğrulama görünür kalır; sonraki adıma siz karar verirsiniz."]],
      primary: "ILAIOS neler üretebilir?",
      secondary: "Nasıl çalışır?",
    },
  },
} as const;

export default function AudiencePage({ locale, audience }: { locale: Locale; audience: Audience }) {
  const c = copy[locale][audience];
  const base = locale === "tr" ? "/tr" : "";
  const isEnterprise = audience === "enterprise";
  const secondaryHref = audience === "enterprise" ? `${base}/architecture` : `${base}/how-it-works`;

  const [visibleOutcomes, setVisibleOutcomes] = useState(Array(c.outcomes.length).fill(false));
  const [visibleOperating, setVisibleOperating] = useState(Array(c.operating.length).fill(false));

  const outcomeRefs = useRef<Array<HTMLDivElement | null>>([]);
  const operatingRefs = useRef<Array<HTMLDivElement | null>>([]);

  const setOutcomeRef = (index: number) => (element: HTMLDivElement | null) => {
    outcomeRefs.current[index] = element;
  };

  const setOperatingRef = (index: number) => (element: HTMLDivElement | null) => {
    operatingRefs.current[index] = element;
  };

  useEffect(() => {
    if (typeof window === "undefined") return;

    const observerOptions = {
      threshold: 0.1,
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = outcomeRefs.current.indexOf(entry.target as HTMLDivElement);
          if (index !== -1) {
            setVisibleOutcomes((prev) => {
              const newArray = [...prev];
              newArray[index] = true;
              return newArray;
            });
          }
        }
      });
    }, observerOptions);

    const operatingObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = operatingRefs.current.indexOf(entry.target as HTMLDivElement);
          if (index !== -1) {
            setVisibleOperating((prev) => {
              const newArray = [...prev];
              newArray[index] = true;
              return newArray;
            });
          }
        }
      });
    }, observerOptions);

    outcomeRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    operatingRefs.current.forEach((ref) => {
      if (ref) operatingObserver.observe(ref);
    });

    return () => {
      observer.disconnect();
      operatingObserver.disconnect();
    };
  }, []);

  return <>
    {/* Hero Section with Motion */}
    <section className={`shell page-hero compact-page-hero pt-20 pb-20 audience-${audience}`}>
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div>
          <div className="eyebrow text-sm tracking-wider text-gray-400">{c.eyebrow}</div>
          <h1 className="text-5xl font-bold tracking-tighter mb-4">{c.title}</h1>
        </div>
        <div className="text-base leading-relaxed mt-4">
          <p className="mb-4">{c.lead}</p>
          <div className="actions flex items-center gap-4">
            <Link
              href={`${base}/factories`}
              className="button bg-gray-900 text-white px-8 py-3 rounded-md font-semibold hover:bg-gray-700 transition-colors duration-200 hover-lift hover-scale"
            >
              {c.primary}
            </Link>
            <Link
              href={secondaryHref}
              className="button secondary border border-gray-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-700 hover:text-white transition-colors duration-200 hover-lift hover-scale"
            >
              {c.secondary}
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell audience-focus">
          <div className="flex flex-col items-start gap-2 max-w-3xl">
            <span className="micro-label text-xs font-bold text-gray-400">{c.focusLabel}</span>
            <h2 className="text-4xl font-bold tracking-tighter mb-4">{c.focusTitle}</h2>
          </div>
          <div className="audience-outcome-list grid gap-8 pt-8">
            {c.outcomes.map(([title, text], index) => (
              <motion.div
                key={title}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className={`border border-text rounded-lg p-6 hover:bg-bg-lighter hover:border-text hover:text-text transition-all duration-200 ${visibleOutcomes[index] ? "visible" : ""} hover-lift hover-scale`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xs font-bold text-gray-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <strong className="text-lg font-semibold">{title}</strong>
                    <p className="text-base leading-relaxed mt-2">{text}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
    <section className="section surface-section pt-24 pb-24">
      <motion.div
        initial={{ x: -20, opacity: 0 }}
        whileInView={{ x: 0, opacity: 1, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
      >
        <div className="shell">
          <div className="compact-heading-row">
            <div className="max-w-3xl">
              <div className="eyebrow text-sm tracking-wider text-gray-400">{locale === "tr" ? "Nasıl ilerler?" : "How it moves"}</div>
              <h2 className="text-3xl font-bold tracking-tighter mb-4">{locale === "tr" ? "Basit talep. Kontrollü çalışma. İncelenebilir sonuç." : "Simple request. Controlled work. Reviewable result."}</h2>
            </div>
          </div>
          <div className="audience-process grid gap-8 pt-8">
            {c.operating.map(([n, title, text], index) => (
              <motion.div
                key={n}
                initial={{ x: -10, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1, transition: { duration: 0.4, delay: index * 0.1 } }}
                className={`border border-text rounded-lg p-6 hover:bg-bg-lighter hover:border-text hover:text-text transition-all duration-200 ${visibleOperating[index] ? "visible" : ""} hover-lift hover-scale`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xs font-bold text-gray-400 shrink-0">{n}</span>
                  <div>
                    <strong className="text-lg font-semibold">{title}</strong>
                    <p className="text-base leading-relaxed mt-2">{text}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </section>
  </>;
}