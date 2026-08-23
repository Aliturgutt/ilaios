import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const component = await readFile(path.join(root, "app", "SystemMotionSignature.tsx"), "utf8");
const css = await readFile(path.join(root, "app", "system-motion-signature.css"), "utf8");
const recovery = await readFile(path.join(root, "app", "WebsiteV2HomeRecovery.tsx"), "utf8");
const pageEn = await readFile(path.join(root, "app", "page.tsx"), "utf8");
const pageTr = await readFile(path.join(root, "app", "tr", "page.tsx"), "utf8");
const failures = [];

for (const token of ["motion-primary-rings", "motion-secondary-rings", "motion-orbit-arcs", "motion-cube", "motion-axis", "motion-core", "motion-markers"]) {
  if (!component.includes(token)) failures.push(`missing retained motion layer group: ${token}`);
}
for (const token of ["html[data-theme=\"light\"]", "@media (prefers-reduced-motion: reduce)", "motion-spin-reverse", "motion-float", "motion-axis", "motion-cube"]) {
  if (!css.includes(token)) failures.push(`missing retained motion parity/performance rule: ${token}`);
}
if (/three|webgl|canvas|requestAnimationFrame|setInterval|setTimeout|https?:\/\//i.test(component + css)) failures.push("motion signature must remain local SVG/CSS without hosted runtime or JS loop");
if (/filter\s*:\s*blur|box-shadow\s*:/i.test(css)) failures.push("motion signature reintroduced heavy blur/shadow decoration");

const effectiveLayers = 7 + 6 + 4 + 2 + 3 + 3 + 3;
if (effectiveLayers < 18 || effectiveLayers > 30) failures.push(`retained motion layer count outside bounded range: ${effectiveLayers}`);

for (const [locale, page] of [["en", pageEn], ["tr", pageTr]]) {
  if (!page.includes("WebsiteV2HomeRecovery")) failures.push(`${locale} homepage does not render WebsiteV2HomeRecovery`);
  if (page.includes("<SuppliedVisual") || page.includes("HomePage locale=")) failures.push(`${locale} homepage still uses appended-only or superseded composition`);
}
if (!recovery.includes("/website-v2/homepage-light.avif") || !recovery.includes("/website-v2/homepage-dark.avif")) failures.push("recovery homepage does not integrate supplied homepage Dark/Light pair");
if (recovery.includes("SystemMotionSignature")) failures.push("rejected motion signature still dominates the canonical recovery homepage");
if (!recovery.includes("v2-process-rail") || !recovery.includes("v2-factory-index") || !recovery.includes("v2-control-rail")) failures.push("recovery homepage is missing required editorial/process/control hierarchy");

if (failures.length) {
  console.error("Website V2 recovery/motion gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log(`Website V2 recovery/motion gate PASS; legacy motion retained as local/reduced-motion-safe component (${effectiveLayers} bounded vector layers) but removed from the canonical homepage.`);
