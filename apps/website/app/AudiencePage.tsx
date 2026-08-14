import Link from "next/link";

type Locale = "en" | "tr";
type Audience = "enterprise" | "individuals";

const copy = {
  en: {
    enterprise: {
      eyebrow: "For enterprises",
      title: "Govern intelligent work without turning model output into operational authority.",
      lead: "ILAIOS is designed for organizations that need repeatable automation and production workflows with explicit identity, policy, permissions, validation, evidence and bounded recovery.",
      pressureTitle: "From fragmented tools to governed outcomes.",
      pressures: [
        ["Operational fragmentation", "Bring recurring work, research and production workflows into an explicit job, policy and evidence model."],
        ["Unbounded AI usage", "Keep model output separate from permission, approval, deterministic validation and acceptance."],
        ["Production overhead", "Use separate Web, Software, App and Video/Media factory workflows instead of one generic generation surface."],
        ["Knowledge fragmentation", "Connect authorized context, project memory, sources and tenant-aware retrieval without making memory an authority source."],
        ["Audit gaps", "Associate material state changes with provenance, validation outcomes and recovery history."],
        ["Failure ambiguity", "Bound retry and repair; stop or escalate when acceptance cannot be established."],
      ],
      operatingTitle: "Governance surrounds execution instead of living inside prompt instructions.",
      operating: [
        ["01", "Admit work", "Identity, tenant, project context, risk and policy define the operating boundary."],
        ["02", "Route capabilities", "Factories, agents, skills and deterministic services receive only the contracts and scopes required for the job."],
        ["03", "Validate independently", "Required checks and approvals decide whether outputs may advance."],
        ["04", "Retain evidence", "Material events, provenance and acceptance context remain reviewable."],
      ],
    },
    individuals: {
      eyebrow: "For individuals",
      title: "Describe the outcome without becoming the operator of an internal AI stack.",
      lead: "ILAIOS is designed to turn personal goals into governed research, web, software, media and operations workflows while keeping state, boundaries and acceptance visible.",
      pressureTitle: "Less tool choreography. More reviewable progress toward the result.",
      pressures: [
        ["Research", "Structure sources, claims and uncertainty instead of relying on an opaque one-shot answer."],
        ["Website work", "Move through requirements, design, implementation and QA toward a verified finished-site outcome."],
        ["Software work", "Keep engineering changes bounded by repository context, tests and review gates."],
        ["Application work", "Keep current review-only App Factory boundaries explicit while the broader application outcome remains canonical product direction."],
        ["Media production", "Coordinate research, script, assets, render and validation through a governed workflow."],
        ["Personal operations", "Prepare reviewable plans for reminders, notes, calendar and email drafts without silently widening authority."],
      ],
      operatingTitle: "A simple request can still have explicit controls underneath.",
      operating: [
        ["01", "State the goal", "Describe what should be finished rather than selecting internal models or providers."],
        ["02", "Keep context bounded", "Identity, project context and permissions define what may participate."],
        ["03", "Execute and validate", "Capabilities work inside scope; required checks decide acceptance."],
        ["04", "Review the result", "Outcome, state and evidence remain visible instead of disappearing into model narration."],
      ],
    },
  },
  tr: {
    enterprise: {
      eyebrow: "Kurumlar için",
      title: "Model çıktısını operasyonel authority'ye dönüştürmeden intelligent work'ü yönetin.",
      lead: "ILAIOS; tekrarlanabilir otomasyon ve production workflow'larına ihtiyaç duyan kurumlar için identity, policy, permissions, validation, evidence ve bounded recovery'yi açık tutacak şekilde tasarlanır.",
      pressureTitle: "Parçalı araçlardan governed outcome'lara.",
      pressures: [
        ["Operasyon parçalanması", "Tekrarlanan iş, research ve production workflow'larını açık job, policy ve evidence modeline bağlayın."],
        ["Unbounded AI kullanımı", "Model çıktısını permission, approval, deterministic validation ve acceptance'tan ayrı tutun."],
        ["Production yükü", "Tek generic generation yüzeyi yerine Web, Software, App ve Video/Media factory'lerini ayrı workflow'lar olarak kullanın."],
        ["Knowledge parçalanması", "Authorized context, project memory, sources ve tenant-aware retrieval'ı memory'yi authority yapmadan bağlayın."],
        ["Audit boşlukları", "Material state değişimlerini provenance, validation sonucu ve recovery geçmişiyle ilişkilendirin."],
        ["Failure belirsizliği", "Retry ve repair'i bounded tutun; acceptance kurulamıyorsa durdurun veya escalation uygulayın."],
      ],
      operatingTitle: "Governance prompt talimatlarının içinde değil, execution'ın çevresindedir.",
      operating: [
        ["01", "İşi kabul et", "Identity, tenant, project context, risk ve policy çalışma sınırını belirler."],
        ["02", "Capability'leri yönlendir", "Factory, agent, skill ve deterministic servisler yalnız iş için gereken contract ve scope'u alır."],
        ["03", "Bağımsız doğrula", "Gerekli kontroller ve approvals output'un ilerleyip ilerleyemeyeceğini belirler."],
        ["04", "Evidence koru", "Material event, provenance ve acceptance context incelenebilir kalır."],
      ],
    },
    individuals: {
      eyebrow: "Bireysel kullanıcılar için",
      title: "Internal AI stack'in operatörü olmadan sonucu tarif edin.",
      lead: "ILAIOS; kişisel hedefleri governed research, web, software, media ve operations workflow'larına dönüştürürken state, boundaries ve acceptance'ı görünür tutmak için tasarlanır.",
      pressureTitle: "Daha az tool choreography. Sonuca doğru daha incelenebilir ilerleme.",
      pressures: [
        ["Research", "Tek seferlik opak cevap yerine source, claim ve uncertainty'yi yapılandırın."],
        ["Web sitesi", "Requirements, design, implementation ve QA üzerinden verified finished-site outcome'a ilerleyin."],
        ["Software", "Engineering değişikliklerini repository context, tests ve review gate'leriyle bounded tutun."],
        ["Application", "Daha geniş application outcome kanonik yön olarak kalırken mevcut review-only App Factory boundary'lerini açık tutun."],
        ["Media production", "Research, script, assets, render ve validation'ı governed workflow ile koordine edin."],
        ["Kişisel operasyon", "Authority'yi sessizce genişletmeden reminder, note, calendar ve email draft planları hazırlayın."],
      ],
      operatingTitle: "Basit bir request'in altında yine de açık kontroller olabilir.",
      operating: [
        ["01", "Hedefi söyle", "Internal model veya provider seçmek yerine neyin bitmesini istediğinizi tarif edin."],
        ["02", "Context'i bounded tut", "Identity, project context ve permissions hangi bilginin kullanılabileceğini belirler."],
        ["03", "Yürüt ve doğrula", "Capability'ler scope içinde çalışır; gerekli kontroller acceptance'ı belirler."],
        ["04", "Sonucu incele", "Outcome, state ve evidence model anlatımının içinde kaybolmadan görünür kalır."],
      ],
    },
  },
} as const;

export default function AudiencePage({ locale, audience }: { locale: Locale; audience: Audience }) {
  const c = copy[locale][audience];
  const tr = locale === "tr";
  const base = tr ? "/tr" : "";
  return <>
    <section className="shell page-hero"><div className="eyebrow">{c.eyebrow}</div><h1>{c.title}</h1><p className="lead">{c.lead}</p><div className="actions"><Link className="button" href={`${base}/factories`}>{tr ? "Factory'leri incele" : "Explore factories"}</Link><Link className="button secondary" href={`${base}/how-it-works`}>{tr ? "Nasıl çalışır?" : "How it works"}</Link></div></section>
    <section className="section"><div className="shell split-copy"><div><div className="eyebrow">{tr ? "Outcome yaklaşımı" : "Outcome approach"}</div><h2>{c.pressureTitle}</h2></div><div><p className="lead small">{tr ? "ILAIOS, business veya personal outcome anlatısını canonical architecture identity'lerinden ayrı tutar. Software Factory ile App Factory ayrı kalır; Knowledge/RAG cross-factory governed plane'dir." : "ILAIOS keeps business or personal outcome language separate from canonical architecture identities. Software Factory and App Factory remain separate; Knowledge/RAG is a cross-factory governed plane."}</p><p className="muted">{tr ? "Current reality ile target truth her capability için ayrıca korunur." : "Current reality and target truth remain distinct for every capability."}</p></div></div></section>
    <section className="section architecture-section"><div className="shell"><div className="process-ledger">{c.pressures.map(([title,text],i)=><article key={title}><span>{String(i+1).padStart(2,"0")}</span><div><h2>{title}</h2><p>{text}</p></div></article>)}</div></div></section>
    <section className="section"><div className="shell"><div className="section-heading"><div><div className="eyebrow">{tr ? "Çalışma modeli" : "Operating model"}</div><h2>{c.operatingTitle}</h2></div><p className="muted">{tr ? "Client'lar authoritative backend state'inin projection'larıdır; model ve provider'lar replaceable resource olarak kalır." : "Clients remain projections of authoritative backend state; models and providers remain replaceable resources."}</p></div><div className="journey-grid">{c.operating.map(([n,title,text])=><article className="journey-card" key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <section className="section"><div className="shell callout"><div><div className="eyebrow">{tr ? "Ürün gerçeği" : "Product truth"}</div><h2>{tr ? "Canonical product direction, public availability demek değildir." : "Canonical product direction is not the same claim as public availability."}</h2></div><div className="actions"><Link className="button" href={`${base}/capabilities`}>{tr ? "Platform yetenekleri" : "Platform capabilities"}</Link><Link className="button secondary" href={`${base}/architecture`}>{tr ? "Mimari" : "Architecture"}</Link></div></div></section>
  </>;
}
