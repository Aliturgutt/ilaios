type Locale = "en" | "tr";

type ArchitectureArea = {
  number: string;
  title: string;
  summary: string;
  items: readonly string[];
};

type ArchitectureGroup = {
  title: string;
  lead: string;
  areas: readonly ArchitectureArea[];
};

const enGroups: readonly ArchitectureGroup[] = [
  {
    title: "Request, identity and planning",
    lead: "The user starts with an outcome. ILAIOS binds that request to authenticated scope, authorized context and explicit acceptance before execution is admitted.",
    areas: [
      { number: "01", title: "Client surfaces", summary: "Ways an authenticated user can request, inspect and receive work.", items: ["Web and authenticated app surfaces", "Desktop product surface", "API / SDK and developer access where published", "Organization and enterprise access paths"] },
      { number: "02", title: "Identity → tenant → project lifecycle", summary: "Execution stays attached to the correct user and organizational scope.", items: ["Authenticated principal", "Tenant / workspace membership", "Project scope", "Roles, sessions and account lifecycle"] },
      { number: "03", title: "Authorized context", summary: "Only context allowed for the current scope should enter the work.", items: ["User and project material", "Authorized external sources", "Context filtering and isolation", "Governed knowledge / RAG"] },
      { number: "04", title: "Goal & acceptance", summary: "The requested outcome is translated into bounded work and review criteria.", items: ["Intent and goal", "Acceptance criteria", "Scope and constraints", "Risk, approval and cost requirements"] },
      { number: "05", title: "Planner & orchestration", summary: "The system structures the work without making the user operate each underlying tool.", items: ["Bounded plan / DAG", "Task and dependency decomposition", "Capability matching", "Retry / alternative planning within limits"] },
      { number: "06", title: "Capability registry", summary: "The system resolves known skills, tools, agents and factory capabilities through one governed catalog.", items: ["Capability identity", "Skill and tool definitions", "Factory matching", "Provider capability mapping"] },
    ],
  },
  {
    title: "Authority and execution admission",
    lead: "Capability does not equal permission. Policy, approval and execution admission remain explicit before consequential work proceeds.",
    areas: [
      { number: "07", title: "Policy gateway & governance", summary: "Central rules determine what execution may do.", items: ["Authentication and authorization", "Tenant isolation", "Data and secret boundaries", "Budget, risk and policy checks"] },
      { number: "08", title: "Human approval", summary: "Consequential actions can pause for an explicit human decision.", items: ["Approval required", "User review", "Approve / reject", "Approval remains bound to the admitted action"] },
      { number: "09", title: "Execution grant", summary: "Approved work receives a bounded execution scope rather than unrestricted authority.", items: ["Allowed tools and actions", "Time / TTL boundaries", "Budget ceiling", "Audit identity and revocation"] },
      { number: "10", title: "Nine production areas", summary: "ILAIOS organizes finished-product work into nine bounded factory families.", items: ["Web", "Video / Media", "Software", "App", "Research / Data", "Security", "Creative / Document", "Commerce / Growth", "Personal Operations"] },
      { number: "11", title: "Execution layer", summary: "Admitted work is performed by governed execution resources.", items: ["Worker", "Skill", "Tool", "Single routing decision", "Replaceable provider"] },
      { number: "12", title: "State machine", summary: "Jobs move through explicit lifecycle states instead of opaque background activity.", items: ["Created / planned", "Approved / running", "Review / completed", "Failed / cancelled"] },
    ],
  },
  {
    title: "Operational lifecycles",
    lead: "Files, releases, schedules, integrations and providers are controlled as operational lifecycles rather than hidden side effects.",
    areas: [
      { number: "13", title: "File & document lifecycle", summary: "Files are treated as governed work inputs and outputs.", items: ["Upload / ingest", "Classification and access", "Format conversion and analysis", "Versioning, export and lifecycle controls"] },
      { number: "14", title: "Deployment & environments", summary: "Delivery progresses through explicit environments and release evidence.", items: ["Development and test", "Staging / preview", "Production release", "CI/CD, health and rollback evidence"] },
      { number: "15", title: "Automation & scheduler", summary: "Repeatable work can be scheduled or triggered inside the same governed runtime.", items: ["Timed schedules", "Event / webhook triggers", "Recurring jobs", "Retry, failure handling and provider selection"] },
      { number: "16", title: "Provider governance", summary: "External execution resources remain replaceable and policy-bound.", items: ["Provider registry and availability", "Cost and capability tracking", "Rate limits and retry", "Privacy, resilience and scaling controls"] },
      { number: "17", title: "API & webhook integrations", summary: "Programmatic access is exposed only where contracts are implemented and published.", items: ["Credential / secret handling", "Authorization", "Webhook and event handling", "Retry, idempotency and failure handling"] },
      { number: "18", title: "Payment & subscription lifecycle", summary: "Commercial access is separated from execution authority and verified before paid access is activated.", items: ["Plans and pricing", "Verified payment activation", "Entitlement / access limits", "Receipts, tax and refund processes where applicable"] },
    ],
  },
  {
    title: "Evidence, operations and company systems",
    lead: "The product keeps evidence, operational state and support systems distinct from model output so results remain reviewable.",
    areas: [
      { number: "19", title: "Notifications & communications", summary: "Meaningful execution and account states can be surfaced through product communication channels.", items: ["Email or in-product messages", "Push / web notifications where available", "User-facing status changes", "Webhook notifications where published"] },
      { number: "20", title: "Evidence & audit", summary: "Material execution events remain traceable independently of model narration.", items: ["Execution and audit records", "Replayable evidence", "User activity and security events", "Cost / operational signals where applicable"] },
      { number: "21", title: "Data & infrastructure", summary: "Application state, authorized knowledge and operational infrastructure support the governed product boundary.", items: ["Application data", "Knowledge / vector retrieval where authorized", "Object storage and cache", "Secrets, backups and infrastructure controls"] },
      { number: "22", title: "Admin & support plane", summary: "Operational administration is separated from customer execution paths.", items: ["Tenant and account administration", "Support and billing operations", "Abuse / incident handling", "Feature and operations controls"] },
      { number: "23", title: "Feedback → improvement loop", summary: "Product improvement uses evidence and user feedback rather than silent self-modification.", items: ["User feedback", "Quality and error analysis", "Evaluation results", "Roadmap and bounded product improvements"] },
      { number: "24", title: "External ecosystem", summary: "External services connect through explicit governed boundaries rather than becoming system authority.", items: ["Repositories and cloud services", "App stores and publishing destinations", "Social / communication services", "Payment and other SaaS integrations where verified"] },
    ],
  },
];

const trGroups: readonly ArchitectureGroup[] = [
  {
    title: "Talep, kimlik ve planlama",
    lead: "Kullanıcı sonuçla başlar. ILAIOS yürütmeye geçmeden önce talebi doğrulanmış kapsam, yetkili bağlam ve açık kabul ölçütlerine bağlar.",
    areas: [
      { number: "01", title: "İstemci yüzeyleri", summary: "Doğrulanmış kullanıcının iş talep ettiği, durumu izlediği ve sonucu aldığı yüzeyler.", items: ["Web ve kimlik doğrulamalı uygulama yüzeyleri", "Masaüstü ürün yüzeyi", "Yayımlandığı ölçüde API / SDK ve geliştirici erişimi", "Kurum ve enterprise erişim yolları"] },
      { number: "02", title: "Kimlik → tenant → proje yaşam döngüsü", summary: "Yürütme doğru kullanıcı ve organizasyon kapsamına bağlı kalır.", items: ["Doğrulanmış principal", "Tenant / workspace üyeliği", "Proje kapsamı", "Roller, oturumlar ve hesap yaşam döngüsü"] },
      { number: "03", title: "Yetkili bağlam", summary: "İşe yalnız mevcut kapsam için izin verilen bağlam girer.", items: ["Kullanıcı ve proje materyali", "Yetkili dış kaynaklar", "Bağlam filtreleme ve izolasyon", "Yönetilen bilgi / RAG"] },
      { number: "04", title: "Hedef ve kabul", summary: "İstenen sonuç sınırları belirli işe ve inceleme ölçütlerine dönüştürülür.", items: ["Niyet ve hedef", "Kabul ölçütleri", "Kapsam ve kısıtlar", "Risk, onay ve maliyet gereksinimleri"] },
      { number: "05", title: "Planlayıcı ve orkestrasyon", summary: "Sistem işi yapılandırır; kullanıcı her alttaki aracı ayrı ayrı işletmek zorunda kalmaz.", items: ["Sınırları belirli plan / DAG", "Görev ve bağımlılık ayrıştırma", "Yetenek eşleme", "Limitler içinde retry / alternatif plan"] },
      { number: "06", title: "Yetenek kataloğu", summary: "Bilinen skill, araç, agent ve factory yetenekleri tek yönetilen katalogdan çözülür.", items: ["Yetenek kimliği", "Skill ve araç tanımları", "Factory eşleme", "Provider yetenek eşleme"] },
    ],
  },
  {
    title: "Yetki ve yürütme kabulü",
    lead: "Yetenek izin anlamına gelmez. Önemli iş ilerlemeden önce politika, onay ve yürütme kabulü açık biçimde çözülür.",
    areas: [
      { number: "07", title: "Policy gateway ve yönetişim", summary: "Merkezi kurallar yürütmenin ne yapabileceğini belirler.", items: ["Kimlik doğrulama ve yetkilendirme", "Tenant izolasyonu", "Veri ve secret sınırları", "Bütçe, risk ve politika kontrolleri"] },
      { number: "08", title: "İnsan onayı", summary: "Sonuç doğuran işlemler açık insan kararı için durabilir.", items: ["Onay gereksinimi", "Kullanıcı incelemesi", "Onayla / reddet", "Onayın kabul edilmiş işleme bağlı kalması"] },
      { number: "09", title: "Yürütme izni", summary: "Onaylı iş sınırsız yetki değil, sınırlandırılmış yürütme kapsamı alır.", items: ["İzin verilen araç ve işlemler", "Zaman / TTL sınırı", "Bütçe tavanı", "Audit kimliği ve iptal"] },
      { number: "10", title: "Dokuz üretim alanı", summary: "ILAIOS bitmiş ürün işini dokuz sınırlandırılmış factory ailesinde düzenler.", items: ["Web", "Video / Medya", "Yazılım", "Uygulama", "Araştırma / Veri", "Güvenlik", "Creative / Doküman", "Commerce / Growth", "Kişisel Operasyon"] },
      { number: "11", title: "Yürütme katmanı", summary: "Kabul edilmiş iş yönetilen yürütme kaynakları tarafından yapılır.", items: ["Worker", "Skill", "Tool", "Tek routing kararı", "Değiştirilebilir provider"] },
      { number: "12", title: "Durum makinesi", summary: "İşler görünmez arka plan faaliyeti yerine açık yaşam döngüsü durumlarından ilerler.", items: ["Created / planned", "Approved / running", "Review / completed", "Failed / cancelled"] },
    ],
  },
  {
    title: "Operasyon yaşam döngüleri",
    lead: "Dosyalar, release, zamanlanmış işler, entegrasyonlar ve provider kullanımı gizli yan etki değil yönetilen yaşam döngüleri olarak ele alınır.",
    areas: [
      { number: "13", title: "Dosya ve doküman yaşam döngüsü", summary: "Dosyalar yönetilen iş girdileri ve çıktıları olarak ele alınır.", items: ["Yükleme / ingest", "Sınıflandırma ve erişim", "Format dönüşümü ve analiz", "Sürümleme, export ve yaşam döngüsü kontrolleri"] },
      { number: "14", title: "Deployment ve ortamlar", summary: "Teslim, açık ortamlar ve release kanıtı üzerinden ilerler.", items: ["Development ve test", "Staging / preview", "Production release", "CI/CD, health ve rollback kanıtı"] },
      { number: "15", title: "Otomasyon ve scheduler", summary: "Tekrarlanabilir işler aynı yönetilen runtime içinde zamanlanabilir veya tetiklenebilir.", items: ["Zamanlanmış görevler", "Event / webhook tetikleyicileri", "Tekrarlayan işler", "Retry, hata yönetimi ve provider seçimi"] },
      { number: "16", title: "Provider yönetişimi", summary: "Dış yürütme kaynakları değiştirilebilir ve politikaya bağlı kalır.", items: ["Provider kataloğu ve erişilebilirlik", "Maliyet ve yetenek takibi", "Rate limit ve retry", "Gizlilik, dayanıklılık ve ölçek kontrolleri"] },
      { number: "17", title: "API ve webhook entegrasyonları", summary: "Programatik erişim yalnız sözleşmeler uygulanıp yayımlandığı ölçüde açılır.", items: ["Credential / secret yönetimi", "Yetkilendirme", "Webhook ve event işleme", "Retry, idempotency ve hata yönetimi"] },
      { number: "18", title: "Ödeme ve abonelik yaşam döngüsü", summary: "Ticari erişim yürütme yetkisinden ayrı tutulur ve ücretli erişim açılmadan önce doğrulanır.", items: ["Planlar ve fiyatlandırma", "Doğrulanmış ödeme ile aktivasyon", "Entitlement / erişim limitleri", "Uygun olduğunda makbuz, vergi ve iade süreçleri"] },
    ],
  },
  {
    title: "Kanıt, operasyon ve şirket sistemleri",
    lead: "Ürün kanıtı, operasyon durumunu ve destek sistemlerini model çıktısından ayrı tutar; böylece sonuçlar incelenebilir kalır.",
    areas: [
      { number: "19", title: "Bildirimler ve iletişim", summary: "Anlamlı yürütme ve hesap durumları ürün iletişim kanallarıyla kullanıcıya taşınabilir.", items: ["E-posta veya ürün içi mesajlar", "Uygun olduğunda push / web bildirimleri", "Kullanıcıya açık durum değişiklikleri", "Yayımlandığı ölçüde webhook bildirimleri"] },
      { number: "20", title: "Kanıt ve audit", summary: "Önemli yürütme olayları model anlatımından bağımsız izlenebilir kalır.", items: ["Execution ve audit kayıtları", "Replay edilebilir kanıt", "Kullanıcı ve güvenlik olayları", "Uygun olduğunda maliyet / operasyon sinyalleri"] },
      { number: "21", title: "Veri ve altyapı", summary: "Uygulama durumu, yetkili bilgi ve operasyon altyapısı yönetilen ürün sınırını destekler.", items: ["Uygulama verisi", "Yetkili knowledge / vector retrieval", "Object storage ve cache", "Secrets, backup ve altyapı kontrolleri"] },
      { number: "22", title: "Admin ve destek katmanı", summary: "Operasyonel yönetim müşteri yürütme yollarından ayrı tutulur.", items: ["Tenant ve hesap yönetimi", "Destek ve faturalama operasyonları", "Abuse / incident yönetimi", "Feature ve operasyon kontrolleri"] },
      { number: "23", title: "Geri bildirim → iyileştirme döngüsü", summary: "Ürün iyileştirme sessiz self-modification yerine kanıt ve kullanıcı geri bildirimiyle yürütülür.", items: ["Kullanıcı geri bildirimi", "Kalite ve hata analizi", "Evaluation sonuçları", "Roadmap ve sınırlandırılmış ürün iyileştirmeleri"] },
      { number: "24", title: "Dış ekosistem", summary: "Dış servisler açık yönetilen sınırlar üzerinden bağlanır; sistem otoritesine dönüşmez.", items: ["Repository ve cloud servisleri", "App store ve yayın hedefleri", "Sosyal / iletişim servisleri", "Doğrulandığı ölçüde ödeme ve diğer SaaS entegrasyonları"] },
    ],
  },
];

const invariants = {
  en: ["One authoritative control plane", "One governed execution runtime", "One routing-decision truth", "One capability / skill identity system", "One evidence / provenance truth"],
  tr: ["Tek authoritative control plane", "Tek yönetilen execution runtime", "Tek routing-decision gerçeği", "Tek capability / skill kimlik sistemi", "Tek evidence / provenance gerçeği"],
} as const;

export default function SystemArchitectureMap({ locale }: { locale: Locale }) {
  const groups = locale === "tr" ? trGroups : enGroups;
  return <div className="system-architecture-map">
    {groups.map(group => <section className="architecture-domain-group" key={group.title}>
      <div className="section-heading"><div><h3>{group.title}</h3></div><p>{group.lead}</p></div>
      <div className="grid three-up architecture-domain-grid">
        {group.areas.map(area => <article className="card architecture-domain-card" key={area.number}>
          <span className="micro-label">{area.number}</span>
          <h4>{area.title}</h4>
          <p>{area.summary}</p>
          <ul>{area.items.map(item => <li key={item}>{item}</li>)}</ul>
        </article>)}
      </div>
    </section>)}
    <section className="architecture-invariants">
      <div className="eyebrow">{locale === "tr" ? "Sistem geneli ilkeler" : "System-wide invariants"}</div>
      <div className="runtime-line">{invariants[locale].map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong></div>)}</div>
    </section>
  </div>;
}
