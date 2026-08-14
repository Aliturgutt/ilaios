import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");
const css = `${await readFile(path.join(app, "adaptive-native.css"), "utf8")}\n${await readFile(path.join(app, "adaptive-structures.css"), "utf8")}`;
const home = await readFile(path.join(app, "HomePage.tsx"), "utf8");
const product = await readFile(path.join(app, "ProductExperience.tsx"), "utf8");
const factory = await readFile(path.join(app, "FactoryExplorer.tsx"), "utf8");
const spatial = await readFile(path.join(app, "SpatialArchitecture.tsx"), "utf8");
const platform = await readFile(path.join(app, "PlatformPage.tsx"), "utf8");
const capabilities = await readFile(path.join(app, "CapabilitiesPage.tsx"), "utf8");
const security = await readFile(path.join(app, "SecurityPage.tsx"), "utf8");
const architecture = await readFile(path.join(app, "ArchitecturePage.tsx"), "utf8");
const audience = await readFile(path.join(app, "AudiencePage.tsx"), "utf8");
const contact = await readFile(path.join(app, "ContactPage.tsx"), "utf8");
const about = await readFile(path.join(app, "AboutPage.tsx"), "utf8");
const chrome = await readFile(path.join(app, "SiteChrome.tsx"), "utf8");

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

const sectionMatch = css.match(/\.section\{[^}]*padding\s*:\s*clamp\([^,]+,[^,]+,\s*([0-9.]+)px/i);
const sectionMax = sectionMatch ? Number(sectionMatch[1]) : null;
if (sectionMax === null || sectionMax > 48) failures.push(`density gate: section max vertical padding must be <= 48px, observed ${sectionMax}`);

forbid(/radial-gradient\s*\(/i, "radial decorative gradient returned");
forbid(/linear-gradient\s*\(/i, "linear decorative gradient returned");
forbid(/text-shadow\s*:/i, "text glow/shadow returned");
forbid(/filter\s*:\s*blur\s*\(/i, "blur decoration returned");
forbid(/#00c2d1|#18c7d9|#2b6fff/i, "legacy neon/cyan-blue palette returned");
for (const match of css.matchAll(/box-shadow\s*:\s*([^;}]+)/gi)) {
  const value = match[1].trim().toLowerCase();
  if (!["none", "initial", "inherit", "unset"].includes(value)) failures.push(`anti-generic gate: non-neutral box shadow returned (${match[1].trim()})`);
}

requireText(home, "ProductExperience", "homepage product visibility");
requireText(home, "FactoryExplorer", "homepage factory interaction");
requireText(home, "SpatialArchitecture", "homepage architecture storytelling");
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
requireText(css, "transform:none!important", "mobile 3D flattening");

requireText(platform, "platform-map-layout", "distinct Platform composition");
requireText(capabilities, "capability-matrix", "distinct Capabilities composition");
requireText(security, "trust-gate", "distinct Security composition");
requireText(architecture, "architecture-primary", "distinct Architecture composition");
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

if (!css.includes("@media(max-width:760px)")) failures.push("responsive gate: dedicated mobile recomposition is missing");
if (!css.includes("@media(prefers-reduced-motion:reduce)")) failures.push("motion gate: reduced-motion fallback is missing");

if (failures.length) {
  console.error("ILAIOS design benchmark gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("ILAIOS design benchmark gate PASS");
console.log(`Benchmarks: ${competitors.join(", ")}`);
for (const question of benchmarkQuestions) console.log(`- ${question}`);
console.log("Manual live-site visual approval remains REQUIRED before the website may be called FINAL.");
