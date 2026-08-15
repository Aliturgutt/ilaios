"use client";

import { useState } from "react";

type Locale = "en" | "tr";
type Item = { title: string; summary: string; description: string; source: string };

const copy: Record<Locale, { hint: string; sourceLabel: string; close: string; items: Item[] }> = {
  en: {
    hint: "Select a control to see what it protects and where the rule comes from.",
    sourceLabel: "Canonical source",
    close: "Close detail",
    items: [
      { title: "Authority", summary: "Requests and model output do not silently widen permissions.", description: "Identity, tenant scope, policy, approvals, tool permissions and budget define the execution boundary. A model or factory may act only inside that admitted authority and cannot self-expand it.", source: "SECURITY_ARCHITECTURE.md · GOVERNANCE.md · IMPLEMENTATION_SPEC.md" },
      { title: "Validation", summary: "Deterministic checks and explicit criteria decide acceptance.", description: "Outputs advance only when the required tests, security gates and acceptance criteria pass. Generation completion is not treated as product completion.", source: "TESTING_AND_EVALUATION.md · IMPLEMENTATION_SPEC.md" },
      { title: "Evidence", summary: "Material outcomes remain inspectable and attributable.", description: "Execution lineage, validation results, provenance and important events are preserved so accepted work can be reviewed and audited without relying on a model's narrative.", source: "GOVERNANCE.md · OBSERVABILITY.md · DATA_ARCHITECTURE.md" },
      { title: "Recovery", summary: "Repair and retry stay bounded; unresolved work stops or escalates.", description: "Checkpoint/resume, retry and repair are permitted only within defined bounds. When those bounds are exhausted, the system stops, records evidence and escalates rather than looping indefinitely.", source: "FAILURE_RECOVERY.md · IMPLEMENTATION_SPEC.md" },
    ],
  },
  tr: {
    hint: "Neyi koruduğunu ve kuralın hangi kanonik kaynaktan geldiğini görmek için bir kontrol seçin.",
    sourceLabel: "Kanonik kaynak",
    close: "Detayı kapat",
    items: [
      { title: "Yetki", summary: "İstekler ve model çıktısı izinleri sessizce genişletmez.", description: "Kimlik, tenant kapsamı, politika, onaylar, araç izinleri ve bütçe yürütme sınırını belirler. Model veya factory yalnız kabul edilmiş yetki içinde hareket edebilir; kendi yetkisini genişletemez.", source: "SECURITY_ARCHITECTURE.md · GOVERNANCE.md · IMPLEMENTATION_SPEC.md" },
      { title: "Doğrulama", summary: "Deterministik kontroller ve açık ölçütler kabulü belirler.", description: "Çıktılar yalnız gerekli testler, güvenlik kapıları ve kabul kriterleri geçtiğinde ilerler. Üretimin tamamlanması ürünün tamamlandığı anlamına gelmez.", source: "TESTING_AND_EVALUATION.md · IMPLEMENTATION_SPEC.md" },
      { title: "Kanıt", summary: "Önemli sonuçlar incelenebilir ve eşleştirilebilir kalır.", description: "Yürütme soyu, doğrulama sonuçları, provenance ve önemli olaylar korunur; böylece kabul edilen iş model anlatımına güvenmeden incelenebilir ve denetlenebilir.", source: "GOVERNANCE.md · OBSERVABILITY.md · DATA_ARCHITECTURE.md" },
      { title: "Kurtarma", summary: "Düzeltme ve yeniden deneme sınırlandırılır; çözülemeyen iş durur veya yükseltilir.", description: "Checkpoint/resume, retry ve repair yalnız tanımlı sınırlar içinde uygulanır. Sınırlar tükendiğinde sistem sonsuz döngüye girmek yerine durur, kanıtı kaydeder ve escalation uygular.", source: "FAILURE_RECOVERY.md · IMPLEMENTATION_SPEC.md" },
    ],
  },
};

export default function GovernanceEvidence({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState<number | null>(null);
  const selected = active === null ? null : c.items[active];

  return <div className="governance-evidence">
    <p className="governance-evidence-hint">{c.hint}</p>
    <div className="evidence-ledger evidence-ledger-interactive">
      {c.items.map((item, index) => <button type="button" key={item.title} className={`evidence-control${active === index ? " is-active" : ""}`} aria-expanded={active === index} aria-controls="governance-evidence-detail" onClick={() => setActive(active === index ? null : index)}>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <div><strong>{item.title}</strong><p>{item.summary}</p></div>
      </button>)}
    </div>
    {selected && <section id="governance-evidence-detail" className="governance-evidence-detail" aria-live="polite">
      <div><span className="micro-label">{String(active! + 1).padStart(2, "0")} · {selected.title}</span><p>{selected.description}</p><small><strong>{c.sourceLabel}:</strong> {selected.source}</small></div>
      <button type="button" className="text-link" onClick={() => setActive(null)} aria-label={c.close}>×</button>
    </section>}
  </div>;
}
