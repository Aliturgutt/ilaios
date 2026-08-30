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
for (const match of css.matchAll(/box-shadow\s*:\s*([^;}]+)/gi)) {
  const value = match[1].trim().toLowerCase();
  if (!["none", "initial", "inherit", "unset"].includes(value)) failures.push(`anti-generic gate: non-neutral box shadow returned (${match[1].trim()})`);
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
requireText(security, "variant=\"runtime\"", "security admission/routing visual");
requireText(architecture, "architecture-primary", "distinct Architecture composition");
requireText(architecture, "variant=\"runtime\"", "architecture admission/routing detail");
requireText(architecture, "variant=\"knowledge\"", "architecture knowledge detail");
requireText(architecture, "variant=\"recovery\"", "architecture recovery detail");
requireText(factoriesPage, "Cross-factory composition", "cross-factory bounded composition");
requireText(factoriesPage, "variant=\"knowledge\"", "factories shared knowledge plane");
requireText(how, "variant=\"journey\"", "English full request chain");
requireText(how, "variant=\"runtime\"", "English execution runtime chain");
requireText(how, "variant=\"recovery\"", "English recovery chain");
requireText(how, "variant=\"cost\"", "English FinOps chain");
requireText(howTr, "variant=\"journey\"", "Turkish full request chain");
requireText(webFactory, "variant=\"web\"", "English full Web Factory lifecycle");
requireText(webFactoryTr, "variant=\"web\"", "Turkish full Web Factory lifecycle");
requireText(audience, "audience-${audience}", "audience-specific rendered composition class");
requireText(audience, "Enterprise control", "Enterprise governance composition");
requireText(audience, "Outcome first", "Individuals outcome composition");
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
console.log("Canonical documentation coverage includes request contracts, admission/routing, knowledge, recovery, FinOps, maturity and the full Web Factory lifecycle.");
console.log("P0 mobile overlap/density invariants are present in the final override layers.");
console.log("Manual live-site visual approval remains REQUIRED before the website may be called FINAL.");
