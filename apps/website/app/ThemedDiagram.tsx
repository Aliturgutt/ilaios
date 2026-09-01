type Props = {
  light: string;
  dark: string;
  alt: string;
  caption?: string;
  priority?: boolean;
  aspect?: "wide" | "portrait";
  className?: string;
};

type DiagramKey =
  | "general-flow"
  | "governance"
  | "verification"
  | "factory-orchestration"
  | "web"
  | "video"
  | "software"
  | "app"
  | "intake";

const EN: Record<DiagramKey, readonly [string, string][]> = {
  "general-flow": [
    ["Sign in + Goal", "Authenticated request"],
    ["Understand", "Intent + requirements"],
    ["Plan", "Bounded work"],
    ["Resolve", "Capabilities + factories"],
    ["Govern", "Policy + approvals"],
    ["Execute", "Admitted workflow"],
    ["Verify", "Checks + repair"],
    ["Deliver", "Result + evidence"],
  ],
  governance: [
    ["Request", "Identity + scope"],
    ["Policy", "Risk + budget"],
    ["Approval", "When required"],
    ["Execute", "Scoped authority"],
    ["Validate", "Independent checks"],
    ["Evidence", "Reviewable trail"],
  ],
  verification: [
    ["Result", "Produced artifact"],
    ["Validate", "Acceptance criteria"],
    ["Evidence", "Capture proof"],
    ["Repair", "Bounded correction"],
    ["Decide", "Accept or stop"],
  ],
  "factory-orchestration": [
    ["Goal", "Requested outcome"],
    ["Understand", "Context + constraints"],
    ["Resolve", "Right capability path"],
    ["Factory", "Specialized production"],
    ["Execute", "Governed workflow"],
    ["Verify", "Acceptance + evidence"],
  ],
  web: [
    ["Request", "Goal + references"],
    ["Analyze", "Audience + structure"],
    ["Design", "System + direction"],
    ["Build", "Site or upgrade"],
    ["Browser QA", "Responsive behavior"],
    ["Verify", "Quality gates"],
    ["Deliver", "Artifact + evidence"],
  ],
  video: [
    ["Request", "Content goal"],
    ["References", "Assets + provenance"],
    ["Plan", "Script + scenes"],
    ["Produce", "Media + audio"],
    ["Render", "Exact artifact"],
    ["Verify", "Technical + content QA"],
    ["Deliver", "Media + evidence"],
  ],
  software: [
    ["Requirement", "Outcome + context"],
    ["Scope", "Bounded plan"],
    ["Implement", "Authorized changes"],
    ["Test", "Deterministic checks"],
    ["Review", "Quality + security"],
    ["Repair", "Bounded correction"],
    ["Deliver", "Tested change"],
  ],
  app: [
    ["Goal", "Product + references"],
    ["UX", "Flows + screens"],
    ["Architecture", "Scope + boundaries"],
    ["Build", "Governed implementation"],
    ["Verify", "Tests + package checks"],
    ["Package", "Platform artifact"],
    ["Readiness", "Release evidence"],
  ],
  intake: [
    ["Goal", "Finished outcome"],
    ["Brand", "Logo + assets"],
    ["References", "Visual direction"],
    ["Existing product", "Website or app"],
    ["Documents", "Data + context"],
    ["Requirements", "Expected behavior"],
    ["Constraints", "Risk + limits"],
    ["Acceptance", "Definition of done"],
  ],
};

const TR: Record<DiagramKey, readonly [string, string][]> = {
  "general-flow": [
    ["Giriş + Hedef", "Kimliği doğrulanmış istek"],
    ["Anla", "Niyet + gereksinimler"],
    ["Planla", "Sınırlandırılmış iş"],
    ["Çözümle", "Yetenekler + factory'ler"],
    ["Yönet", "Politika + onaylar"],
    ["Yürüt", "Kabul edilmiş workflow"],
    ["Doğrula", "Kontroller + onarım"],
    ["Teslim et", "Sonuç + kanıt"],
  ],
  governance: [
    ["İstek", "Kimlik + kapsam"],
    ["Politika", "Risk + bütçe"],
    ["Onay", "Gerektiğinde"],
    ["Yürüt", "Sınırlı yetki"],
    ["Doğrula", "Bağımsız kontroller"],
    ["Kanıt", "İncelenebilir iz"],
  ],
  verification: [
    ["Sonuç", "Üretilmiş artifact"],
    ["Doğrula", "Kabul ölçütleri"],
    ["Kanıt", "Proof kaydı"],
    ["Onar", "Sınırlandırılmış düzeltme"],
    ["Karar", "Kabul et veya dur"],
  ],
  "factory-orchestration": [
    ["Hedef", "İstenen sonuç"],
    ["Anla", "Bağlam + kısıtlar"],
    ["Çözümle", "Doğru yetenek yolu"],
    ["Factory", "Uzmanlaşmış üretim"],
    ["Yürüt", "Yönetilen workflow"],
    ["Doğrula", "Kabul + kanıt"],
  ],
  web: [
    ["İstek", "Hedef + referanslar"],
    ["Analiz", "Kitle + yapı"],
    ["Tasarım", "Sistem + yön"],
    ["Build", "Site veya upgrade"],
    ["Browser QA", "Responsive davranış"],
    ["Doğrula", "Kalite kapıları"],
    ["Teslim et", "Artifact + kanıt"],
  ],
  video: [
    ["İstek", "İçerik hedefi"],
    ["Referans", "Varlıklar + provenance"],
    ["Plan", "Senaryo + sahneler"],
    ["Üret", "Medya + ses"],
    ["Render", "Exact artifact"],
    ["Doğrula", "Teknik + içerik QA"],
    ["Teslim et", "Medya + kanıt"],
  ],
  software: [
    ["Gereksinim", "Sonuç + bağlam"],
    ["Kapsam", "Sınırlandırılmış plan"],
    ["Uygula", "Yetkili değişiklik"],
    ["Test", "Deterministik kontroller"],
    ["Review", "Kalite + güvenlik"],
    ["Onar", "Sınırlandırılmış düzeltme"],
    ["Teslim et", "Test edilmiş değişiklik"],
  ],
  app: [
    ["Hedef", "Ürün + referanslar"],
    ["UX", "Akışlar + ekranlar"],
    ["Mimari", "Kapsam + sınırlar"],
    ["Build", "Yönetilen implementasyon"],
    ["Doğrula", "Test + paket kontrolleri"],
    ["Paketle", "Platform artifact"],
    ["Readiness", "Release kanıtı"],
  ],
  intake: [
    ["Hedef", "Bitmiş sonuç"],
    ["Marka", "Logo + varlıklar"],
    ["Referans", "Görsel yön"],
    ["Mevcut ürün", "Web sitesi veya app"],
    ["Doküman", "Veri + bağlam"],
    ["Gereksinim", "Beklenen davranış"],
    ["Kısıt", "Risk + limitler"],
    ["Kabul", "Tamamlanma ölçütü"],
  ],
};

function diagramKey(path: string, aspect: Props["aspect"]): DiagramKey {
  if (aspect === "portrait") return "intake";
  const file = path.split("/").pop() ?? "";
  const key = file.replace(/-(dark|light)\.(avif|webp|png)$/i, "") as DiagramKey;
  if (!(key in EN)) throw new Error(`Unknown ILAIOS diagram key: ${key}`);
  return key;
}

export default function ThemedDiagram({
  dark,
  alt,
  caption,
  aspect = "wide",
  className = "",
}: Props) {
  const key = diagramKey(dark, aspect);
  const isTurkish = /[çğıöşüİ]/.test(alt);
  const stages = (isTurkish ? TR : EN)[key];

  return (
    <figure className={`themed-diagram native-diagram ${aspect === "portrait" ? "is-portrait" : ""} ${className}`.trim()}>
      <div className="native-diagram-track" role="img" aria-label={alt} data-diagram-key={key}>
        {stages.map(([title, detail], index) => (
          <div className="native-diagram-node" key={title}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{title}</strong>
            <small>{detail}</small>
            {index < stages.length - 1 ? <i aria-hidden="true">→</i> : null}
          </div>
        ))}
      </div>
      {caption ? <figcaption>{caption}</figcaption> : null}
    </figure>
  );
}
