type Locale = "en" | "tr";

type ArchitectureArea = readonly [number, string, string];

type ArchitectureGroup = {
  title: string;
  lead: string;
  areas: readonly ArchitectureArea[];
};

const copy = {
  en: {
    eyebrow: "End-to-end system architecture",
    title: "The public architecture view covers the complete ILAIOS operating model.",
    lead: "These areas explain how a request moves from an authenticated client surface to governed execution, verification, delivery and ongoing operations. Public wording describes implemented behavior conservatively and keeps target-only capabilities distinct from verified availability.",
    groups: [
      {
        title: "Experience, identity and context",
        lead: "Requests start from a user-facing surface and stay tied to authenticated organizational and project context.",
        areas: [
          [1, "Client surfaces", "Web, Desktop, mobile, CLI, API and organization-facing surfaces provide controlled entry points without owning execution authority."],
          [2, "Identity → tenant → project lifecycle", "Authentication, principal identity, tenant membership, project scope, role and session state keep work bound to the correct organizational context."],
          [3, "Authorized context", "Memory, RAG, project data and permitted external context are filtered by scope and authority before use."],
        ],
      },
      {
        title: "Intent, planning and capability selection",
        lead: "The requested outcome becomes an explicit plan with acceptance criteria and bounded capability choices.",
        areas: [
          [4, "Goal & acceptance", "User intent, constraints, acceptance criteria, risk, cost and approval needs are resolved before work advances."],
          [5, "Planner & orchestration", "Work is decomposed into bounded dependencies, ordered tasks, retries and execution stages rather than an unrestricted autonomous loop."],
          [6, "Capability registry", "Skills, tools, agents, providers and factory mappings are resolved through one governed capability identity system."],
        ],
      },
      {
        title: "Governance and execution admission",
        lead: "Capability does not equal permission; consequential work must pass policy and approval boundaries first.",
        areas: [
          [7, "Policy gateway & governance", "Authorization, tenant isolation, data classification, tool permission, commercial rules and budget controls determine what may proceed."],
          [8, "Human approval", "Where risk or policy requires it, a human approval decision is bound to the exact action and scope before execution."],
          [9, "Execution grant", "Admitted work receives bounded permission, limits, expiry, audit identity and revocation semantics for the authorized execution."],
        ],
      },
      {
        title: "Nine native production areas",
        lead: "ILAIOS uses nine bounded factory families on the shared governed runtime. Knowledge/RAG is shared context, not a tenth factory.",
        areas: [
          [10, "Factory layer", "Web; Video / Media; Software; App; Research / Data; Security; Creative / Document; Commerce / Growth; and Personal Operations share one control model while preserving domain-specific workflows."],
        ],
      },
      {
        title: "Execution, state and delivery",
        lead: "Admitted work runs through one governed runtime and a reviewable lifecycle.",
        areas: [
          [11, "Execution layer", "Workers, skills, tools, one routing decision and replaceable providers perform only admitted work inside the shared runtime."],
          [12, "State machine", "Created, planned, approved, running, review, completed, failed and cancelled states keep execution lifecycle explicit and recoverable."],
          [13, "File & document lifecycle", "Uploads, classification, conversion, review, deployment or export remain scoped, versioned and permission-aware."],
          [14, "Deployment & environments", "Development, testing, staging, preview and production paths remain distinct and release evidence is kept separate from build intent."],
        ],
      },
      {
        title: "Automation, providers and integrations",
        lead: "Background execution and external services remain governed resources rather than independent authorities.",
        areas: [
          [15, "Automation & scheduler", "Scheduled, event-driven and background work uses bounded retries, idempotency, error handling and provider scoring where implemented."],
          [16, "Provider governance", "Provider availability, health, cost, privacy, capability mapping, rate limits and replacement remain controlled behind the routing boundary."],
          [17, "API & webhook integrations", "Credentials, authorization, webhook handling, retries and failure behavior are published only where the corresponding interface is implemented and verified."],
        ],
      },
      {
        title: "Commercial, communication and evidence",
        lead: "Commercial access, user communication and system proof remain observable and reviewable.",
        areas: [
          [18, "Payment & subscription lifecycle", "Plans, checkout, entitlement and payment verification are separated from the public Website; final commercial access is activated only through the verified product/payment path."],
          [19, "Notifications & communications", "Product notifications and communication channels are treated as governed delivery capabilities and are described publicly only to the extent they are implemented."],
          [20, "Evidence & audit", "Execution evidence, provenance, audit trail, state transitions and acceptance records support independent review of what actually happened."],
        ],
      },
      {
        title: "Platform operations and ecosystem",
        lead: "Shared infrastructure and operations support the product without becoming separate product authorities.",
        areas: [
          [21, "Data & infrastructure", "Application data, authorized knowledge, object storage, secrets, cache, backups and retention are governed platform responsibilities; implementation detail is exposed only where useful and verified."],
          [22, "Admin & support plane", "Tenant support, account and billing support, incidents, abuse/risk operations, feature management and operational administration remain controlled platform functions."],
          [23, "Feedback → improvement loop", "User feedback, quality signals, failure analysis and evidence can inform bounded product improvement without self-modifying runtime authority."],
          [24, "External ecosystem", "Repositories, cloud services, app stores, social platforms, email, payments and other SaaS/API systems remain external integrations with explicit authorization boundaries."],
        ],
      },
    ] as readonly ArchitectureGroup[],
  },
  tr: {
    eyebrow: "Uçtan uca sistem mimarisi",
    title: "Kamusal mimari görünümü ILAIOS işletim modelinin tamamını kapsar.",
    lead: "Bu alanlar bir talebin doğrulanmış kullanıcı yüzeyinden yönetilen yürütmeye, doğrulamaya, teslimata ve operasyonlara nasıl ilerlediğini açıklar. Kamusal metin yalnız kanıtlanan davranışı mevcut gibi anlatır; hedef olan yetenekleri doğrulanmış kullanılabilirlikten ayırır.",
    groups: [
      {
        title: "Deneyim, kimlik ve bağlam",
        lead: "İstek kullanıcı yüzeyinden başlar ve doğrulanmış organizasyon ile proje bağlamına bağlı kalır.",
        areas: [
          [1, "Kullanıcı yüzeyleri", "Web, Masaüstü, mobil, CLI, API ve organizasyon yüzeyleri kontrollü giriş noktaları sağlar; yürütme otoritesinin sahibi olmaz."],
          [2, "Kimlik → tenant → proje yaşam döngüsü", "Kimlik doğrulama, principal, tenant üyeliği, proje kapsamı, rol ve oturum durumu işi doğru organizasyon bağlamına bağlar."],
          [3, "Yetkili bağlam", "Memory, RAG, proje verileri ve izin verilen dış bağlam kullanılmadan önce kapsam ve yetkiye göre filtrelenir."],
        ],
      },
      {
        title: "Niyet, planlama ve yetenek seçimi",
        lead: "İstenen sonuç açık kabul ölçütleri ve sınırlandırılmış yetenek seçimleri olan bir plana dönüşür.",
        areas: [
          [4, "Hedef ve kabul ölçütleri", "Kullanıcı niyeti, kısıtlar, kabul ölçütleri, risk, maliyet ve onay ihtiyacı iş ilerlemeden önce çözülür."],
          [5, "Planlayıcı ve orkestrasyon", "İş sınırsız otonom döngü yerine sınırları belli bağımlılıklara, görevlere, retry'lara ve yürütme aşamalarına ayrılır."],
          [6, "Yetenek kataloğu", "Skill, tool, agent, provider ve factory eşleşmeleri tek yönetilen capability identity sistemi üzerinden çözülür."],
        ],
      },
      {
        title: "Yönetişim ve yürütme kabulü",
        lead: "Yetenek izin anlamına gelmez; önemli işler önce politika ve onay sınırlarından geçer.",
        areas: [
          [7, "Policy gateway ve yönetişim", "Yetkilendirme, tenant izolasyonu, veri sınıflandırma, tool izni, ticari kurallar ve bütçe kontrolleri neyin ilerleyebileceğini belirler."],
          [8, "İnsan onayı", "Risk veya politika gerektiriyorsa insan onayı yürütmeden önce exact işlem ve kapsama bağlanır."],
          [9, "Yürütme izni", "Kabul edilen işe süre, limit, audit kimliği ve iptal kuralları olan sınırlandırılmış yürütme yetkisi verilir."],
        ],
      },
      {
        title: "Dokuz yerel üretim alanı",
        lead: "ILAIOS, ortak yönetilen runtime üzerinde dokuz sınırlandırılmış factory ailesi kullanır. Knowledge/RAG ortak bağlamdır; onuncu fabrika değildir.",
        areas: [
          [10, "Factory katmanı", "Web; Video / Medya; Yazılım; Uygulama; Araştırma / Veri; Güvenlik; Creative / Doküman; Commerce / Büyüme ve Kişisel Operasyon aynı kontrol modelini paylaşırken alanlarına özgü iş akışlarını korur."],
        ],
      },
      {
        title: "Yürütme, durum ve teslimat",
        lead: "Kabul edilen iş tek yönetilen runtime ve incelenebilir bir yaşam döngüsü üzerinden ilerler.",
        areas: [
          [11, "Yürütme katmanı", "Worker, skill, tool, tek routing decision ve değiştirilebilir provider'lar yalnız kabul edilmiş işi ortak runtime içinde yürütür."],
          [12, "Durum makinesi", "Created, planned, approved, running, review, completed, failed ve cancelled durumları yürütme yaşam döngüsünü açık ve kurtarılabilir tutar."],
          [13, "Dosya ve doküman yaşam döngüsü", "Yükleme, sınıflandırma, dönüştürme, inceleme, deployment veya export işlemleri kapsamlı, sürümlü ve izin kontrollü kalır."],
          [14, "Deployment ve ortamlar", "Development, test, staging, preview ve production yolları ayrıdır; release kanıtı build niyetinden ayrı tutulur."],
        ],
      },
      {
        title: "Otomasyon, sağlayıcılar ve entegrasyonlar",
        lead: "Arka plan yürütmesi ve dış servisler bağımsız otorite değil yönetilen kaynaklar olarak kalır.",
        areas: [
          [15, "Otomasyon ve scheduler", "Zamanlanmış, event tabanlı ve arka plan işleri uygulandığı ölçüde sınırlandırılmış retry, idempotency, hata yönetimi ve provider scoring kullanır."],
          [16, "Provider governance", "Provider erişilebilirliği, sağlık, maliyet, gizlilik, yetenek eşleme, rate limit ve değiştirilebilirlik routing sınırının arkasında yönetilir."],
          [17, "API ve webhook entegrasyonları", "Credential, authorization, webhook, retry ve failure davranışları yalnız ilgili interface uygulanıp doğrulandığı ölçüde yayımlanır."],
        ],
      },
      {
        title: "Ticari erişim, iletişim ve kanıt",
        lead: "Ticari erişim, kullanıcı iletişimi ve sistem kanıtı gözlemlenebilir ve incelenebilir kalır.",
        areas: [
          [18, "Ödeme ve abonelik yaşam döngüsü", "Plan, checkout, entitlement ve ödeme doğrulama kamusal Website'ten ayrıdır; nihai ticari erişim yalnız doğrulanmış ürün/ödeme yoluyla etkinleşir."],
          [19, "Bildirimler ve iletişim", "Ürün bildirimleri ve iletişim kanalları yönetilen teslimat yetenekleridir ve yalnız uygulandıkları ölçüde kamusal olarak anlatılır."],
          [20, "Kanıt ve audit", "Yürütme kanıtı, provenance, audit trail, state transition ve kabul kayıtları gerçekte ne olduğunu bağımsız incelemeyi destekler."],
        ],
      },
      {
        title: "Platform operasyonları ve dış ekosistem",
        lead: "Paylaşılan altyapı ve operasyonlar ürünü destekler; ayrı ürün otoritelerine dönüşmez.",
        areas: [
          [21, "Veri ve altyapı", "Uygulama verisi, yetkili bilgi, object storage, secrets, cache, backup ve retention yönetilen platform sorumluluklarıdır; detay yalnız faydalı ve doğrulanmış olduğu yerde gösterilir."],
          [22, "Admin ve destek katmanı", "Tenant desteği, hesap ve ödeme desteği, incident, abuse/risk operations, feature yönetimi ve operasyonel yönetim kontrollü platform fonksiyonlarıdır."],
          [23, "Geri bildirim → iyileştirme döngüsü", "Kullanıcı geri bildirimi, kalite sinyali, hata analizi ve kanıt sınırlandırılmış ürün iyileştirmesini besleyebilir; runtime otoritesi kendi kendini değiştirmez."],
          [24, "Dış ekosistem", "Repository'ler, cloud servisleri, app store'lar, sosyal platformlar, e-posta, ödeme ve diğer SaaS/API sistemleri açık yetkilendirme sınırları olan dış entegrasyonlar olarak kalır."],
        ],
      },
    ] as readonly ArchitectureGroup[],
  },
} as const;

export default function SystemArchitectureMap({ locale }: { locale: Locale }) {
  const c = copy[locale];
  return <section className="section surface-section" data-visual-role="system-architecture-map">
    <div className="shell">
      <div className="section-heading"><div><div className="eyebrow">{c.eyebrow}</div><h2>{c.title}</h2></div><p>{c.lead}</p></div>
      <div className="architecture-layer-list">
        {c.groups.map((group, groupIndex) => <article key={group.title} className="card">
          <span>{String(groupIndex + 1).padStart(2, "0")}</span>
          <strong>{group.title}</strong>
          <p>{group.lead}</p>
          <div className="boundary-ledger" style={{gridTemplateColumns:"repeat(auto-fit, minmax(220px, 1fr))"}}>
            {group.areas.map(([number, title, detail]) => <div key={number} className="card">
              <span>{String(number).padStart(2, "0")}</span>
              <strong>{title}</strong>
              <p>{detail}</p>
            </div>)}
          </div>
        </article>)}
      </div>
    </div>
  </section>;
}
