"use client";

import { useState } from "react";

type Locale = "en" | "tr";
type Item = { title: string; summary: string; description: string };

const copy: Record<Locale, { hint: string; items: Item[] }> = {
  en: {
    hint: "Select a control to see what it protects and how it behaves.",
    items: [
      { title: "Authority", summary: "Requests and model output do not silently widen permissions.", description: "Identity, tenant scope, policy, approvals, tool permissions and budget define the execution boundary. A model or factory may act only inside that admitted authority and cannot self-expand it." },
      { title: "Validation", summary: "Deterministic checks and explicit criteria decide acceptance.", description: "Outputs advance only when the required tests, security gates and acceptance criteria pass. Generation completion is not treated as product completion." },
      { title: "Evidence", summary: "Material outcomes remain inspectable and attributable.", description: "Execution lineage, validation results, provenance and important events are preserved so accepted work can be reviewed and audited without relying on a model's narrative." },
      { title: "Recovery", summary: "Repair and retry stay bounded; unresolved work stops or escalates.", description: "Checkpoint/resume, retry and repair are permitted only within defined bounds. When those bounds are exhausted, the system stops, records evidence and escalates rather than looping indefinitely." },
    ],
  },
  tr: {
    hint: "Neyi koruduğunu ve nasıl davrandığını görmek için bir kontrol seçin.",
    items: [
      { title: "Yetki", summary: "İstekler ve model çıktısı izinleri sessizce genişletmez.", description: "Kimlik, tenant kapsamı, politika, onaylar, araç izinleri ve bütçe yürütme sınırını belirler. Model veya factory yalnız kabul edilmiş yetki içinde hareket edebilir; kendi yetkisini genişletemez." },
      { title: "Doğrulama", summary: "Deterministik kontroller ve açık ölçütler kabulü belirler.", description: "Çıktılar yalnız gerekli testler, güvenlik kapıları ve kabul kriterleri geçtiğinde ilerler. Üretimin tamamlanması ürünün tamamlandığı anlamına gelmez." },
      { title: "Kanıt", summary: "Önemli sonuçlar incelenebilir ve eşleştirilebilir kalır.", description: "Yürütme soyu, doğrulama sonuçları, provenance ve önemli olaylar korunur; böylece kabul edilen iş model anlatımına güvenmeden incelenebilir ve denetlenebilir." },
      { title: "Kurtarma", summary: "Düzeltme ve yeniden deneme sınırlandırılır; çözülemeyen iş durur veya yükseltilir.", description: "Checkpoint/resume, retry ve repair yalnız tanımlı sınırlar içinde uygulanır. Sınırlar tükendiğinde sistem sonsuz döngüye girmek yerine durur, kanıtı kaydeder ve escalation uygular." },
    ],
  },
};

export default function GovernanceEvidence({ locale }: { locale: Locale }) {
  const c = copy[locale];
  const [active, setActive] = useState(0);
  const selected = c.items[active];

  return <div className="governance-evidence">
    <p className="governance-evidence-hint">{c.hint}</p>
    <div className="evidence-ledger evidence-ledger-interactive">
      {c.items.map((item, index) => <button type="button" key={item.title} className={`evidence-control${active === index ? " is-active" : ""}`} aria-pressed={active === index} aria-controls="governance-evidence-detail" onClick={() => setActive(index)}>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <div><strong>{item.title}</strong><p>{item.summary}</p></div>
      </button>)}
    </div>
    <section id="governance-evidence-detail" className="governance-evidence-detail" aria-live="polite">
      <div><span className="micro-label">{String(active + 1).padStart(2, "0")} · {selected.title}</span><p>{selected.description}</p></div>
    </section>
  </div>;
}
