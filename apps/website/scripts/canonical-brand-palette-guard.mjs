import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");
const palette = await readFile(path.join(app, "brand-palette.css"), "utf8");
const finalLayer = await readFile(path.join(app, "site-v2-finalization.css"), "utf8");

const failures = [];
const requireText = (source, text, label) => {
  if (!source.includes(text)) failures.push(`${label}: missing ${text}`);
};
const forbid = (source, pattern, label) => {
  if (pattern.test(source)) failures.push(`${label}: forbidden legacy palette value returned`);
};

for (const token of [
  "--brand-carbon: #0A0A0A;",
  "--brand-charcoal: #141414;",
  "--brand-graphite: #1E1E1E;",
  "--brand-stone: #2A2A2A;",
  "--brand-white: #FFFFFF;",
  "--brand-text-secondary: #E6E6E6;",
  "--brand-text-tertiary: #B3B3B3;",
  "--brand-disabled: #808080;",
  "--brand-hover: #242424;",
  "--brand-active: #2F2F2F;",
]) requireText(palette, token, "canonical palette");

requireText(palette, "--brand-logo-cyan: #00C2D1;", "reserved logo identity");
requireText(palette, "--brand-logo-blue: #146BFF;", "reserved logo identity");
requireText(palette, "--brand-cyan: var(--brand-text-secondary);", "legacy cyan compatibility alias");
requireText(palette, "--brand-blue: var(--brand-text-secondary);", "legacy blue compatibility alias");
requireText(palette, "--v2-cyan: var(--brand-text-secondary);", "legacy V2 cyan bridge");
requireText(palette, "--v2-blue: var(--brand-text-secondary);", "legacy V2 blue bridge");

forbid(finalLayer, /#00c2d1|#146bff|#009fbd|#1769d2|#0b0f14|#111827|#1f2937|#334155|#5c58fe/i, "final loaded website layer");
forbid(finalLayer, /rgba\(0\s*,\s*194\s*,\s*209/i, "final loaded website layer cyan rgba");

requireText(finalLayer, "--accent: #2A2A2A;", "light neutral accent");
requireText(finalLayer, "--accent-2: #2F2F2F;", "light neutral secondary accent");
requireText(finalLayer, "--v2-cyan: #E6E6E6;", "final V2 cyan neutral lock");
requireText(finalLayer, "--v2-blue: #E6E6E6;", "final V2 blue neutral lock");

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Canonical brand palette guard PASS");
