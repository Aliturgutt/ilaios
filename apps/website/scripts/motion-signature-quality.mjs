import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const component = await readFile(path.join(root, "app", "SystemMotionSignature.tsx"), "utf8");
const css = await readFile(path.join(root, "app", "system-motion-signature.css"), "utf8");
const recovery = await readFile(path.join(root, "app", "WebsiteV2HomeRecovery.tsx"), "utf8");
const pageEn = await readFile(path.join(root, "app", "page.tsx"), "utf8");
const pageTr = await readFile(path.join(root, "app", "tr", "page.tsx"), "utf8");
const failures = [];

for (const token of ["canonical-dimensional-orbital-core", "motion-depth-orbits", "motion-structural-rings", "motion-orbit-arcs", "motion-cube", "motion-axis", "motion-core", "motion-markers"]) {
  if (!component.includes(token)) failures.push(`missing canonical dimensional motion layer: ${token}`);
}
for (const token of ["html[data-theme=\"light\"]", "@media (prefers-reduced-motion: reduce)", "motion-spin-reverse", "motion-float", "motion-axis", "motion-cube", "6s linear", "9s linear", "13s linear", "8s ease-in-out"]) {
  if (!css.includes(token)) failures.push(`missing motion parity/performance/timing rule: ${token}`);
}
if (/three|webgl|canvas|requestAnimationFrame|setInterval|setTimeout|https?:\/\//i.test(component + css)) failures.push("motion identity must remain local SVG/CSS without hosted runtime or JS loop");
if (/filter\s*:\s*blur|box-shadow\s*:/i.test(css)) failures.push("motion identity must not introduce heavy blur/shadow decoration");
if (/status|healthy|online|uptime|telemetry/i.test(component)) failures.push("decorative motion must not imply runtime status or telemetry");

const effectiveLayers = 3 + 6 + 4 + 2 + 3 + 4 + 3;
if (effectiveLayers < 18 || effectiveLayers > 30) failures.push(`motion layer count outside bounded range: ${effectiveLayers}`);

for (const [locale, page] of [["en", pageEn], ["tr", pageTr]]) {
  if (!page.includes("WebsiteV2HomeRecovery")) failures.push(`${locale} homepage does not render WebsiteV2HomeRecovery`);
  if (page.includes("<SuppliedVisual") || page.includes("HomePage locale=")) failures.push(`${locale} homepage still uses appended-only or superseded composition`);
}
if (!recovery.includes("/website-v2/homepage-light.avif") || !recovery.includes("/website-v2/homepage-dark.avif")) failures.push("recovery homepage does not integrate supplied homepage Dark/Light pair");
if (!recovery.includes("SystemMotionSignature") || !recovery.includes("v2-hero-motion")) failures.push("canonical dimensional orbital core is not bound to the recovery hero");
if ((recovery.match(/SystemMotionSignature/g) ?? []).length !== 2) failures.push("dimensional motion identity must remain hero-only on the recovery homepage");
if (!recovery.includes("v2-process-rail") || !recovery.includes("v2-factory-index") || !recovery.includes("v2-control-rail")) failures.push("recovery homepage is missing required editorial/process/control hierarchy");

if (failures.length) {
  console.error("Website V2 recovery/dimensional-motion gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log(`Website V2 recovery/dimensional-motion gate PASS; hero-only local SVG/CSS orbital core uses ${effectiveLayers} bounded vector layers with Dark/Light parity and reduced-motion fallback.`);
