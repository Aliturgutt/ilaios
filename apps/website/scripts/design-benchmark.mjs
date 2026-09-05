import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");
const nativeCss = await readFile(path.join(app, "adaptive-native.css"), "utf8");
const structureCss = await readFile(path.join(app, "adaptive-structures.css"), "utf8");
const mobileCss = await readFile(path.join(app, "mobile-redteam.css"), "utf8");
const canonicalCss = await readFile(path.join(app, "canonical-detail.css"), "utf8");
const finalCss = await readFile(path.join(app, "site-v2-finalization.css"), "utf8");
const css = `${nativeCss}\n${structureCss}\n${mobileCss}\n${canonicalCss}\n${finalCss}`;
const home = await readFile(path.join(app, "HomePage.tsx"), "utf8");
const homeEntry = await readFile(path.join(app, "page.tsx"), "utf8");
const homeEntryTr = await readFile(path.join(app, "tr", "page.tsx"), "utf8");
const product = await readFile(path.join(app, "ProductExperience.tsx"), "utf8");
const factory = await readFile(path.join(app, "FactoryExplorer.tsx"), "utf8");
const factoriesPage = await readFile(path.join(app, "FactoriesPage.tsx"), "utf8");
const spatial = await readFile(path.join(app, "SpatialArchitecture.tsx"), "utf8");
const systemVisuals = await readFile(path.join(app, "SystemVisuals.tsx"), "utf8");
const canonicalDetail = await readFile(path.join(app, "CanonicalSystemDetail.tsx"), "utf8");
const platform = await readFile(path.join(app, "PlatformPage.tsx"), "utf8");
const capabilities = await readFile(path.join(app, "CapabilitiesPage.tsx"), "utf8");
const security = await readFile(path.join(app, "SecurityPage.tsx"), "utf8");
const architecture = await readFile(path.join(app, "ArchitecturePage.tsx"), "utf8");
const audience = await readFile(path.join(app, "AudiencePage.tsx"), "utf8");
const contact = await readFile(path.join(app, "ContactPage.tsx"), "utf8");
const about = await readFile(path.join(app, "AboutPage.tsx"), "utf8");
const useIlaios = await readFile(path.join(app, "UseILAIOSPage.tsx"), "utf8");
const resources = await readFile(path.join(app, "resources", "page.tsx"), "utf8");
const resourcesTr = await readFile(path.join(app, "tr", "resources", "page.tsx"), "utf8");
const privacy = await readFile(path.join(app, "privacy", "page.tsx"), "utf8");
const privacyTr = await readFile(path.join(app, "tr", "privacy", "page.tsx"), "utf8");
const core = await readFile(path.join(app, "core", "page.tsx"), "utf8");
const coreTr = await readFile(path.join(app, "tr", "core", "page.tsx"), "utf8");
const chrome = await readFile(path.join(app, "SiteChrome.tsx"), "utf8");
const layout = await readFile(path.join(app, "layout.tsx"), "utf8");
const how = await readFile(path.join(app, "how-it-works", "page.tsx"), "utf8");
const howTr = await readFile(path.join(app, "tr", "how-it-works", "page.tsx"), "utf8");
const webFactory = await readFile(path.join(app, "factories", "web", "page.tsx"), "utf8");
const webFactoryTr = await readFile(path.join(app, "tr", "factories", "web", "page.tsx"), "utf8");

const competitors = ["Manus", "Lovable", "Replit", "v0", "Framer", "Devin"];
const benchmarkQuestions = [
  "Is ILAIOS wasting more vertical space than the benchmark set?",
  "Is typography unnecessarily large?",
  "Is the product visible instead of merely described?",
  "Does the page feel static when the product model is dynamic?",
  "Has the design fallen back to repeated generic cards?",
  "Would a human product designer plausibly approve the rendered composition?",
];

const failures = [];
function requireText(source, text, label) {
  if (!source.includes(text)) failures.push(`${label}: missing ${text}`);
}
function forbid(pattern, label) {
  if (pattern.test(css)) failures.push(`anti-generic gate: ${label}`);
}
function forbidIn(source, pattern, label) {
  if (pattern.test(source)) failures.push(`${label}: forbidden internal detail returned`);
}
function clampMax(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = css.match(new RegExp(`${escaped}\\{[^}]*font-size\\s*:\\s*clamp\\([^,]+,[^,]+,\\s*([0-9.]+)rem`, "i"));
  return match ? Number(match[1]) : null;
}

const h1Max = clampMax("h1");
const h2Max = clampMax("h2");
if (h1Max === null || h1Max > 3.1) failures.push(`density gate: h1 max must be <= 3.1rem, observed ${h1Max}`);
if (h2Max === null || h2Max > 1.9) failures.push(`density gate: h2 max must be <= 1.9rem, observed ${h2Max}`);

forbid(/radial-gradient\s*\(/i, "radial decorative gradient returned");
forbid(/linear-gradient\s*\(/i, "linear decorative gradient returned");
forbid(/text-shadow\s*:/i, "text glow/shadow returned");
forbid(/filter\s*:\s*blur\s*\(/i, "blur decoration returned");
forbid(/#00c2d1|#18c7d9|#2b6fff/i, "legacy neon/cyan-blue palette returned");
const canonicalNeutralColors = new Set([
  "#0a0a0a",
  "#141414",
  "#1e1e1e",
  "#2a2a2a",
  "#ffffff",
  "#e6e6e6",
  "#b3b3b3",
  "#808080",
  "#242424",
  "#2f2f2f",
]);
for (const match of css.matchAll(/box-shadow\s*:\s*([^;}]+)/gi)) {
  const rawValue = match[1].trim();
  const value = rawValue.toLowerCase().replace(/\s*!important\s*$/i, "").trim();
  if (["none", "initial", "inherit", "unset"].includes(value)) continue;
  const colors = [...value.matchAll(/#[0-9a-f]{6}\b/gi)].map((color) => color[0].toLowerCase());
  if (!colors.length || colors.some((color) => !canonicalNeutralColors.has(color))) {
    failures.push(`anti-generic gate: non-neutral box shadow returned (${rawValue})`);
  }
}

requireText(layout, "mobile-redteam.css", "mobile correction layer");
requireText(layout, "canonical-detail.css", "canonical documentation visual layer");
requireText(homeEntry, "HomePage", "English canonical homepage entrypoint");
requireText(homeEntryTr, "HomePage", "Turkish canonical homepage entrypoint");
if (homeEntry.includes("WebsiteV2HomeRecovery") || homeEntryTr.includes("WebsiteV2HomeRecovery")) failures.push("homepage entrypoint: legacy WebsiteV2HomeRecovery still active");
requireText(home, "homepage-v2-authoritative", "authoritative homepage identity");
requireText(home, "ProductExperience", "homepage product visibility");
requireText(home, "home-process-rail-v2", "five-step execution composition");
requireText(home, "home-output-index-v2", "restrained production index");
requireText(home, "home-control-ledger-v2", "governed control composition");
requireText(home, "GovernanceEvidence", "homepage evidence credibility");
requireText(product, "Planning", "interactive product state progression");
requireText(product, "Building", "interactive product state progression");
requireText(product, "Validating", "interactive product state progression");
requireText(product, "Finished", "interactive product state progression");
requireText(product, "Interactive canonical workflow preview", "prototype truth label");
requireText(product, "no external side effects", "prototype truth boundary");
requireText(factory, "onMouseEnter", "factory hover behavior");
requireText(factory, "factory-pipeline", "factory pipeline preview");
requireText(spatial, "onPointerMove", "spatial pointer depth");
requireText(spatial, "addEventListener(\"scroll\"", "spatial scroll depth");

for (const role of ["governed-execution-diagram", "control-execution-plane-diagram", "factory-lifecycle-diagram", "trust-boundary-diagram"]) requireText(systemVisuals, role, "canonical system visual role");
for (const role of ["canonical-request-chain", "admission-routing-runtime", "authorized-knowledge-plane", "checkpoint-bounded-repair", "finops-routing-flow", "capability-maturity-model", "web-factory-full-lifecycle"]) requireText(canonicalDetail, role, "canonical documentation visual role");
for (const term of ["ExecutionGrant", "RoutingDecision", "Tenant isolation", "Quality floor", "Bounded plan / DAG", "DESIGNED", "DEPLOYED / PRODUCTION", "Browser QA", "Security QA", "Visual QA", "Bounded repair"]) requireText(canonicalDetail, term, "canonical detail coverage");

requireText(platform, "platform-map-layout", "distinct Platform composition");
requireText(platform, "variant=\"journey\"", "platform identity/request contract visual");
requireText(platform, "variant=\"knowledge\"", "platform knowledge visual");
requireText(capabilities, "capability-matrix", "distinct Capabilities composition");
requireText(capabilities, "variant=\"maturity\"", "capability maturity truth");
requireText(capabilities, "variant=\"cost\"", "capability FinOps routing truth");
requireText(security, "trust-gate", "distinct Security composition");
requireText(security, "Missing required authority, validation or evidence stops sensitive work.", "English Security fail-closed boundary");
requireText(security, "Gerekli yetki, doğrulama veya kanıt eksikse hassas iş ilerlemez.", "Turkish Security fail-closed boundary");
requireText(security, "security@ilaios.com", "verified Security reporting route");
forbidIn(security, /CanonicalSystemDetail|variant=\"runtime\"|ExecutionGrant|RoutingDecision|worker lease|fencing/i, "public Security technical-density boundary");

requireText(architecture, "architecture-primary", "distinct Architecture composition");
requireText(architecture, "One control authority. Multiple governed ways to get work done.", "outcome-readable Architecture hierarchy");
requireText(architecture, "SystemVisuals", "Architecture governed execution visual");
requireText(architecture, "Technical depth", "Architecture progressive technical disclosure");
forbidIn(architecture, /CanonicalSystemDetail|ExecutionGrant|RoutingDecision|worker lease|fencing token|Knowledge \/ RAG|Checkpoint \/ Resume \/ Repair/i, "Architecture public-density boundary");

requireText(factoriesPage, "Cross-factory composition", "cross-factory bounded composition");
requireText(factoriesPage, "variant=\"knowledge\"", "factories shared knowledge plane");

for (const text of [
  "Describe what you want finished",
  "ILAIOS organizes the work",
  "The work is produced",
  "ILAIOS verifies and delivers",
  "Goal → governed work → production → verification → delivery.",
  "What verified means",
  'href="/use-ilaios"',
]) requireText(how, text, "English public How It Works flow");
for (const text of [
  "Bitmesini istediğin sonucu tarif et",
  "ILAIOS işi düzenler",
  "İş üretilir",
  "ILAIOS doğrular ve teslim eder",
  "Hedef → yönetilen iş → üretim → doğrulama → teslim.",
  "Doğrulanmış ne demek?",
  'href="/tr/use-ilaios"',
]) requireText(howTr, text, "Turkish public How It Works flow");
forbidIn(how, /ExecutionGrant|RoutingDecision|worker lease|fencing token|admission lease/i, "English How It Works boundary");
forbidIn(howTr, /ExecutionGrant|RoutingDecision|worker lease|fencing token|admission lease/i, "Turkish How It Works boundary");

requireText(webFactory, "variant=\"web\"", "English full Web Factory lifecycle");
requireText(webFactoryTr, "variant=\"web\"", "Turkish full Web Factory lifecycle");
requireText(audience, "audience-${audience}", "audience-specific rendered composition class");
requireText(audience, "What teams can move forward", "Enterprise outcome composition");
requireText(audience, "Outcome first", "Individuals outcome composition");
forbidIn(audience, /operational authority|execution spine|canonical product direction|deployment and general availability/i, "audience public technical-density boundary");

requireText(useIlaios, "Describe the finished result. ILAIOS manages the path to it.", "Use ILAIOS outcome-first hero");
requireText(useIlaios, "Different outcomes, one governed product boundary.", "Use ILAIOS outcome grouping");
forbidIn(useIlaios, /ilaios-concept\.avif|Product-flow concept|Static illustrative workflow|ThemedDiagram|next\/image/i, "Use ILAIOS fake-or-static product-screen boundary");

requireText(resources, "Resources explains the thinking; Docs carries the technical reference.", "English Resources/Docs separation");
requireText(resourcesTr, "Resources yaklaşımı açıklar; Docs teknik referansı taşır.", "Turkish Resources/Docs separation");
requireText(resources, "detail-directory", "Resources compact editorial directory");
requireText(resourcesTr, "detail-directory", "Turkish Resources compact editorial directory");

requireText(privacy, "This notice describes the public ILAIOS marketing website.", "English Privacy marketing/product boundary");
requireText(privacyTr, "Bu bildirim kamuya açık ILAIOS pazarlama sitesini açıklar.", "Turkish Privacy marketing/product boundary");
requireText(privacy, "privacy@ilaios.com", "English Privacy verified public contact");
requireText(privacyTr, "privacy@ilaios.com", "Turkish Privacy verified public contact");

requireText(core, "One control authority around every governed execution.", "English Core authority hierarchy");
requireText(coreTr, "Her yönetilen yürütmenin çevresinde tek kontrol otoritesi.", "Turkish Core authority hierarchy");
forbidIn(core, /ProductDeepDive|RoutingDecision|ExecutionGrant|worker lease|fencing/i, "English Core technical-density boundary");
forbidIn(coreTr, /ProductDeepDive|RoutingDecision|ExecutionGrant|worker lease|fencing/i, "Turkish Core technical-density boundary");

requireText(contact, "contact-directory", "compact Contact directory");
requireText(about, "about-editorial-grid", "compact About editorial composition");
requireText(chrome, "footer-nav-grid", "dense footer information architecture");
for (const label of ["Product", "Use", "Resources", "Trust", "Company"]) requireText(chrome, `\"${label}\"`, "footer information architecture");

const requiredVisualRoles = ["interactive-product-demo", "five-step-execution", "factory-explorer", "architecture-spatial-map", "contact-directory"];
const combined = [home, product, factory, spatial, contact].join("\n");
for (const role of requiredVisualRoles) requireText(combined, role, "rendered visual role");

requireText(mobileCss, "@media (max-width:760px)", "dedicated mobile breakpoint");
requireText(mobileCss, "grid-template-columns:1fr!important", "mobile one-column recomposition");
requireText(mobileCss, ".process-rail{display:grid!important;grid-template-columns:1fr!important", "mobile vertical execution timeline");
requireText(mobileCss, ".factory-index{display:grid!important;grid-template-columns:1fr!important", "mobile factory accordion flow");
requireText(mobileCss, ".spatial-stage{transform:none!important", "mobile 3D flattening");
requireText(mobileCss, "position:static!important", "mobile overlap neutralization");
requireText(mobileCss, "min-height:0!important", "mobile auto-height protection");
requireText(mobileCss, "overflow-x:hidden", "mobile horizontal overflow protection");
requireText(mobileCss, "@media (prefers-reduced-motion:reduce)", "motion fallback");
requireText(canonicalCss, "@media(max-width:760px)", "canonical detail mobile breakpoint");
requireText(canonicalCss, ".canonical-dual{grid-template-columns:1fr", "canonical dual-stack mobile recomposition");
requireText(canonicalCss, ".canonical-linear{display:grid;grid-template-columns:1fr", "canonical linear mobile timeline");

if (failures.length) {
  console.error("ILAIOS design benchmark gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("ILAIOS design benchmark gate PASS");
console.log(`Benchmarks: ${competitors.join(", ")}`);
for (const question of benchmarkQuestions) console.log(`- ${question}`);
console.log("Technical reference components retain request contracts, admission/routing, knowledge, recovery, FinOps, maturity and full Web Factory lifecycle coverage.");
console.log("Public marketing surfaces stay outcome-first while detailed authority internals remain in Architecture/Docs/Core only at the appropriate abstraction level.");
console.log("P0 mobile overlap/density invariants are present in the final correction layers.");
console.log("Manual live-site visual approval remains REQUIRED before the website may be called FINAL.");
