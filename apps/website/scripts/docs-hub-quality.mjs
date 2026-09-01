import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd(), "app");
const en = await readFile(path.join(root, "docs", "page.tsx"), "utf8");
const tr = await readFile(path.join(root, "tr", "docs", "page.tsx"), "utf8");
const failures = [];

function requireText(source, text, label) {
  if (!source.includes(text)) failures.push(`${label}: missing ${text}`);
}

for (const [source, label, terms] of [
  [en, "English docs hub", ["Architecture", "Security", "Core", "Execution", "Evidence", "API", "Recovery", "/platform/execution", "/platform/evidence"]],
  [tr, "Turkish docs hub", ["Mimari", "Güvenlik", "Core", "Yürütme", "Kanıt", "API", "Kurtarma", "/tr/platform/execution", "/tr/platform/evidence"]],
]) {
  for (const term of terms) requireText(source, term, label);
  requireText(source, "compact-page-hero", label);
  requireText(source, "detail-directory", label);
}

if (/href=["'`]\/[^"'`]*(?:api|recovery)/i.test(en) || /href=["'`]\/tr\/[^"'`]*(?:api|recovery|kurtarma)/i.test(tr)) {
  failures.push("Docs hub must not expose unverified API/recovery routes as live links.");
}

if (failures.length) {
  console.error("Docs hub quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Docs hub quality gate PASS");
