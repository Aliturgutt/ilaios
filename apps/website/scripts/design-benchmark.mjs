import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");
const nativeCss = await readFile(path.join(app, "adaptive-native.css"), "utf8");
const structureCss = await readFile(path.join(app, "adaptive-structures.css"), "utf8");
const mobileCss = await readFile(path.join(app, "mobile-redteam.css"), "utf8");
const css = `${nativeCss}\n${structureCss}\n${mobileCss}`;
const home = await readFile(path.join(app, "HomePage.tsx"), "utf8");
const product = await readFile(path.join(app, "ProductExperience.tsx"), "utf8");
const factory = await readFile(path.join(app, "FactoryExplorer.tsx"), "utf8");
const spatial = await readFile(path.join(app, "SpatialArchitecture.tsx"), "utf8");
const systemVisuals = await readFile(path.join(app, "SystemVisuals.tsx"), "utf8");
const platform = await readFile(path.join(app, "PlatformPage.tsx"), "utf8");
const capabilities = await readFile(path.join(app, "CapabilitiesPage.tsx"), "utf8");
const security = await readFile(path.join(app, "SecurityPage.tsx"), "utf8");
const architecture = await readFile(path.join(app, "ArchitecturePage.tsx"), "utf8");
const audience = await readFile(path.join(app, "AudiencePage.tsx"), "utf8");
const contact = await readFile(path.join(app, "ContactPage.tsx"), "utf8");
const about = await readFile(path.join(app, "AboutPage.tsx"), "utf8");
const chrome = await readFile(path.join(app, "SiteChrome.tsx"), "utf8");
const layout = await readFile(path.join(app, "layout.tsx"), "utf8");

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
requireText(home, "ProductExperience", "homepage product visibility");
requireText(home, "FactoryExplorer", "homepage factory interaction");
requireText(home, "SpatialArchitecture", "homepage architecture storytelling");
requireText(home, "SystemVisuals", "homepage canonical visual storytelling");
requireText(home, "process-rail", "five-step execution composition");
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

for (const role of ["governed-execution-diagram", "control-execution-plane-diagram", "factory-lifecycle-diagram", "trust-boundary-diagram"]) {
  requireText(systemVisuals, role, "canonical system visual role");
}
requireText(systemVisuals, "Goal", "governed execution goal node");
requireText(systemVisuals, "Policy", "governed execution policy node");
requireText(systemVisuals, "Router", "governed execution router node");
requireText(systemVisuals, "Validation", "governed execution validation node");
requireText(systemVisuals, "Evidence", "governed execution evidence node");
requireText(systemVisuals, "Request", "factory lifecycle request stage");
requireText(systemVisuals, "Deliver", "factory lifecycle delivery stage");

requireText(platform, "platform-map-layout", "distinct Platform composition");
requireText(platform, "variant=\"planes\"", "platform control/execution visual");
requireText(capabilities, "capability-matrix", "distinct Capabilities composition");
requireText(security, "trust-gate", "distinct Security composition");
requireText(security, "variant=\"trust\"", "security trust-boundary visual");
requireText(architecture, "architecture-primary", "distinct Architecture composition");
requireText(architecture, "variant=\"execution\"", "architecture execution visual");
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

/* P0 mobile source-level invariants. Runtime browser certification remains the rendered truth gate. */
requireText(mobileCss, "@media (max-width:760px)", "dedicated mobile breakpoint");
requireText(mobileCss, "grid-template-columns:1fr!important", "mobile one-column recomposition");
requireText(mobileCss, ".process-rail{display:grid!important;grid-template-columns:1fr!important", "mobile vertical execution timeline");
requireText(mobileCss, ".factory-index{display:grid!important;grid-template-columns:1fr!important", "mobile factory accordion flow");
requireText(mobileCss, ".spatial-stage{transform:none!important", "mobile 3D flattening");
requireText(mobileCss, "position:static!important", "mobile overlap neutralization");
requireText(mobileCss, "min-height:0!important", "mobile auto-height protection");
requireText(mobileCss, "overflow-x:hidden", "mobile horizontal overflow protection");
requireText(mobileCss, "@media (prefers-reduced-motion:reduce)", "motion fallback");

if (failures.length) {
  console.error("ILAIOS design benchmark gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("ILAIOS design benchmark gate PASS");
console.log(`Benchmarks: ${competitors.join(", ")}`);
for (const question of benchmarkQuestions) console.log(`- ${question}`);
console.log("P0 mobile overlap/density invariants are present in the final override layer.");
console.log("Manual live-site visual approval remains REQUIRED before the website may be called FINAL.");
