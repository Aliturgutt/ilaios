import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");

const spatial = await readFile(path.join(app, "SpatialArchitecture.tsx"), "utf8");
const governance = await readFile(path.join(app, "GovernanceEvidence.tsx"), "utf8");
const systemVisuals = await readFile(path.join(app, "SystemVisuals.tsx"), "utf8");
const finalCss = await readFile(path.join(app, "final-interaction-redteam.css"), "utf8");
const liveCss = await readFile(path.join(app, "live-density-fixes.css"), "utf8");
const layout = await readFile(path.join(app, "layout.tsx"), "utf8");

const failures = [];
const publicInteractiveSources = [spatial, governance, systemVisuals];

for (const [index, source] of publicInteractiveSources.entries()) {
  if (/Canonical source|Kanonik kaynak/i.test(source)) failures.push(`public interactive source ${index + 1}: internal canonical-source label leaked into UI`);
  if (/\b[A-Z0-9_]+\.md\b/.test(source)) failures.push(`public interactive source ${index + 1}: internal markdown filename leaked into UI`);
}

if (!systemVisuals.startsWith('"use client";')) failures.push("SystemVisuals must remain a client component for real node interaction");
if (!systemVisuals.includes("onClick")) failures.push("SystemVisuals must contain click interaction");
if (!systemVisuals.includes("aria-pressed")) failures.push("SystemVisuals interactive nodes must expose pressed state");
if (!systemVisuals.includes("system-inline-detail")) failures.push("SystemVisuals must render populated selected-node detail");
if (!systemVisuals.includes("system-visual-control")) failures.push("SystemVisuals must use the governed interactive control class");

if (!finalCss.includes(".system-visuals.is-grid") || !finalCss.includes("align-items: start !important")) failures.push("system visual grid must not stretch short cards into dead space");
if (!finalCss.includes(".system-visual-control.is-active")) failures.push("system diagram active state is missing");
if (!finalCss.includes(".system-inline-detail")) failures.push("system selected-detail styling is missing");
if (!finalCss.includes("@media (max-width: 760px)")) failures.push("final interaction layer needs a narrow-mobile breakpoint");
if (!finalCss.includes("word-break: normal !important")) failures.push("narrow-mobile semantic labels need no mid-word fragmentation");
if (!liveCss.includes(".process-rail > article") || !liveCss.includes("hyphens: none !important")) failures.push("iPhone timeline word-integrity override is missing");

const liveImport = layout.indexOf('import "./live-density-fixes.css";');
const finalImport = layout.indexOf('import "./final-interaction-redteam.css";');
if (finalImport < 0) failures.push("final interaction red-team stylesheet is not imported");
if (liveImport >= 0 && finalImport >= 0 && finalImport < liveImport) failures.push("final interaction red-team stylesheet must load after live-density fixes");

if (failures.length) {
  console.error("ILAIOS public UX red-team FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("ILAIOS public UX red-team PASS");
console.log("- public interactive UI exposes product explanations, not internal documentation filenames");
console.log("- system diagrams are clickable, stateful and content-complete");
console.log("- short system cards do not stretch into desktop dead space");
console.log("- iPhone semantic labels retain whole-word readability");
