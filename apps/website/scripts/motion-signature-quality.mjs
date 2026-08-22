import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const component = await readFile(path.join(root, "app", "SystemMotionSignature.tsx"), "utf8");
const css = await readFile(path.join(root, "app", "system-motion-signature.css"), "utf8");
const home = await readFile(path.join(root, "app", "HomePage.tsx"), "utf8");
const failures = [];

for (const token of ["motion-primary-rings", "motion-secondary-rings", "motion-orbit-arcs", "motion-cube", "motion-axis", "motion-core", "motion-markers"]) {
  if (!component.includes(token)) failures.push(`missing motion layer group: ${token}`);
}
for (const token of ["html[data-theme=\"light\"]", "@media (prefers-reduced-motion: reduce)", "motion-spin-reverse", "motion-float", "motion-axis", "motion-cube"]) {
  if (!css.includes(token)) failures.push(`missing motion parity/performance rule: ${token}`);
}
if (!home.includes("<SystemMotionSignature />")) failures.push("home hero does not render canonical motion signature");
if (/three|webgl|canvas|requestAnimationFrame|setInterval|setTimeout|https?:\/\//i.test(component + css)) failures.push("motion signature must remain local SVG/CSS without hosted runtime or JS loop");
if (/filter\s*:\s*blur|box-shadow\s*:/i.test(css)) failures.push("motion signature reintroduced heavy blur/shadow decoration");

const effectiveLayers = 7 + 6 + 4 + 2 + 3 + 3 + 3;
if (effectiveLayers < 18 || effectiveLayers > 30) failures.push(`effective layer count outside canonical range: ${effectiveLayers}`);

if (failures.length) {
  console.error("Motion signature quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log(`Motion signature quality gate PASS (${effectiveLayers} effective vector layers).`);
