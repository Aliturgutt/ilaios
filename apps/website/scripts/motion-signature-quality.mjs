import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const recovery = await readFile(path.join(root, "app", "WebsiteV2HomeRecovery.tsx"), "utf8");
const pageEn = await readFile(path.join(root, "app", "page.tsx"), "utf8");
const pageTr = await readFile(path.join(root, "app", "tr", "page.tsx"), "utf8");
const supplied = await readFile(path.join(root, "app", "SuppliedVisual.tsx"), "utf8");
const packageJson = await readFile(path.join(root, "package.json"), "utf8");
const failures = [];

for (const [locale, page] of [["en", pageEn], ["tr", pageTr]]) {
  if (!page.includes("WebsiteV2HomeRecovery")) failures.push(`${locale} homepage does not render WebsiteV2HomeRecovery`);
  if (page.includes("<SuppliedVisual") || page.includes("HomePage locale=")) failures.push(`${locale} homepage still uses appended-only or superseded composition`);
}

for (const forbidden of [
  "SystemMotionSignature",
  "v2-hero-motion",
  "motion-cube",
  "orbital-core",
  "canonical-dimensional-orbital-core",
]) {
  if (recovery.includes(forbidden)) failures.push(`corporate homepage still contains rejected motion identity: ${forbidden}`);
}

if (/spline|three(?:\.js)?|webgl|react-three|@react-three/i.test(packageJson)) {
  failures.push("corporate website must not depend on Spline/Three/WebGL decorative runtime");
}

for (const token of [
  "/website-v2/homepage-light.avif",
  "/website-v2/homepage-dark.avif",
  "v2-process-rail",
  "v2-control-rail",
  "v2-factory-index",
  "v2-evidence",
  "/factories",
  "/how-it-works",
  "/architecture",
  "/capabilities",
]) {
  if (!recovery.includes(token)) failures.push(`corporate homepage is missing required hierarchy/control: ${token}`);
}

for (const token of ["aspect-ratio:1672/941", "object-fit:contain", "html[data-theme=\"light\"]"]) {
  if (!supplied.includes(token)) failures.push(`supplied visual contract is missing responsive/theme rule: ${token}`);
}

const sectionCount = (recovery.match(/<section\b/g) ?? []).length;
if (sectionCount < 5 || sectionCount > 7) failures.push(`corporate homepage section count must remain concise (5-7), found ${sectionCount}`);
if (/status|healthy|online|uptime|telemetry/i.test(recovery)) failures.push("corporate homepage must not imply unverified runtime health/telemetry");

if (failures.length) {
  console.error("Website corporate visual-quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Website corporate visual-quality gate PASS; ${sectionCount} concise sections, supplied Dark/Light visual contract, and no rejected cube/orbit/3D hero dependency.`);
