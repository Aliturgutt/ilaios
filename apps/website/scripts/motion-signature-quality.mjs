import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const home = await readFile(path.join(root, "app", "HomePage.tsx"), "utf8");
const pageEn = await readFile(path.join(root, "app", "page.tsx"), "utf8");
const pageTr = await readFile(path.join(root, "app", "tr", "page.tsx"), "utf8");
const supplied = await readFile(path.join(root, "app", "SuppliedVisual.tsx"), "utf8");
const packageJson = await readFile(path.join(root, "package.json"), "utf8");
const failures = [];

for (const [locale, page] of [["en", pageEn], ["tr", pageTr]]) {
  if (!page.includes("HomePage")) failures.push(`${locale} homepage does not render canonical HomePage`);
  if (page.includes("WebsiteV2HomeRecovery")) failures.push(`${locale} homepage still renders legacy WebsiteV2HomeRecovery`);
}

for (const forbidden of [
  "SystemMotionSignature",
  "v2-hero-motion",
  "motion-cube",
  "orbital-core",
  "canonical-dimensional-orbital-core",
  "<SuppliedVisual",
]) {
  if (home.includes(forbidden)) failures.push(`corporate homepage still contains rejected hero composition: ${forbidden}`);
}

if (/spline|three(?:\.js)?|webgl|react-three|@react-three/i.test(packageJson)) {
  failures.push("corporate website must not depend on Spline/Three/WebGL decorative runtime");
}

for (const token of [
  "homepage-v2-authoritative",
  "ProductExperience",
  "home-process-rail-v2",
  "home-control-ledger-v2",
  "home-output-index-v2",
  "GovernanceEvidence",
  "/factories",
  "/how-it-works",
  "/architecture",
  "/capabilities",
]) {
  if (!home.includes(token)) failures.push(`corporate homepage is missing required hierarchy/control: ${token}`);
}

for (const token of ["aspect-ratio:1672/941", "object-fit:contain", "html[data-theme=\"light\"]"]) {
  if (!supplied.includes(token)) failures.push(`supplied visual contract is missing responsive/theme rule: ${token}`);
}

const sectionCount = (home.match(/<section\b/g) ?? []).length;
if (sectionCount < 6 || sectionCount > 8) failures.push(`corporate homepage section count must remain concise (6-8), found ${sectionCount}`);
if (/status|healthy|online|uptime|telemetry/i.test(home)) failures.push("corporate homepage must not imply unverified runtime health/telemetry");

if (failures.length) {
  console.error("Website corporate visual-quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Website corporate visual-quality gate PASS; ${sectionCount} concise sections, canonical product surface, and no rejected cube/orbit/3D hero dependency.`);
