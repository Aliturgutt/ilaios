import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd());
const app = path.join(root, "app");
const forbiddenPublicMailboxes = [
  "aws-root@ilaios.com",
  "operations@ilaios.com",
  "billing@ilaios.com",
  "cloud@ilaios.com",
  "postmaster@ilaios.com",
];
const unverifiedFunctionalMailboxes = [
  "info@ilaios.com",
  "support@ilaios.com",
  "privacy@ilaios.com",
  "security@ilaios.com",
  "abuse@ilaios.com",
];
const requiredPublicMailboxes = ["contact@ilaios.com"];
const requiredSocial = [
  "https://www.linkedin.com/company/ilaios/",
  "https://x.com/ilaios",
];

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir)) {
    const full = path.join(dir, entry);
    const info = await stat(full);
    if (info.isDirectory()) out.push(...await walk(full));
    else if (/\.(?:tsx?|css|mjs|json)$/.test(entry)) out.push(full);
  }
  return out;
}

const files = await walk(app);
const fileTexts = await Promise.all(files.map(async file => ({ file, text: await readFile(file, "utf8") })));
const source = fileTexts.map(({ file, text }) => `${file}\n${text}`).join("\n");
const failures = [];

for (const mailbox of forbiddenPublicMailboxes) {
  if (source.includes(`mailto:${mailbox}`)) failures.push(`forbidden public mailbox exposed: ${mailbox}`);
}
for (const mailbox of unverifiedFunctionalMailboxes) {
  if (source.includes(mailbox)) failures.push(`unverified functional mailbox published before verification: ${mailbox}`);
}

function mailboxIsLinked(mailbox) {
  return fileTexts.some(({ text }) => {
    if (text.includes(`mailto:${mailbox}`)) return true;
    const mappedMailto = text.includes('href={`mailto:${email}`}') || text.includes("href={'mailto:' + email}") || text.includes('href={"mailto:" + email}');
    return mappedMailto && text.includes(`"${mailbox}"`);
  });
}

for (const mailbox of requiredPublicMailboxes) {
  if (!mailboxIsLinked(mailbox)) failures.push(`required public mailbox missing or not linked: ${mailbox}`);
}
for (const social of requiredSocial) {
  if (!source.includes(social)) failures.push(`verified social URL missing: ${social}`);
}

const routes = files.filter(file => file.endsWith(`${path.sep}page.tsx`));
for (const file of routes) {
  const rel = path.relative(app, file).replaceAll(path.sep, "/");
  const text = await readFile(file, "utf8");
  if (!text.includes("metadata") && !text.includes("generateMetadata")) {
    failures.push(`route lacks metadata declaration: ${rel}`);
  }
}

const sitemap = await readFile(path.join(app, "sitemap.ts"), "utf8");
const robots = await readFile(path.join(app, "robots.ts"), "utf8");
if (!sitemap.includes("/tr")) failures.push("sitemap does not enumerate Turkish routes");
if (!robots.includes("sitemap")) failures.push("robots metadata does not publish sitemap");

const layout = await readFile(path.join(app, "layout.tsx"), "utf8");
if (!layout.includes("https://ilaios.com") && !layout.includes("NEXT_PUBLIC_SITE_URL")) {
  failures.push("root layout lacks canonical site URL authority");
}

const siteChrome = await readFile(path.join(app, "SiteChrome.tsx"), "utf8");
if (!/<a\b[^>]*href=["']#main-content["'][^>]*>/.test(siteChrome)) {
  failures.push("site chrome lacks a skip link targeting the main landmark");
}
if (!/<main\b[^>]*id=["']main-content["'][^>]*tabIndex=\{-1\}[^>]*>/.test(siteChrome)) {
  failures.push("main landmark must remain programmatically focusable without joining the Tab order");
}

// ILAIOS public-site visual policy: the final override layer must remain restrained,
// compact, high-contrast and free from generic generator-style neon/glow decoration.
// Older compatibility layers may retain historical declarations only when the final
// loaded overrides explicitly neutralize them.
const adaptiveNative = await readFile(path.join(app, "adaptive-native.css"), "utf8");
const adaptiveStructures = await readFile(path.join(app, "adaptive-structures.css"), "utf8");
const finalVisualSource = `${adaptiveNative}\n${adaptiveStructures}`;
const forbiddenFinalVisualPatterns = [
  ["radial gradient", /radial-gradient\s*\(/i],
  ["linear gradient", /linear-gradient\s*\(/i],
  ["text shadow", /text-shadow\s*:/i],
  ["blur filter", /filter\s*:\s*blur\s*\(/i],
  ["cyan translucent glow fill", /rgba\(\s*0\s*,\s*194\s*,\s*209\s*,/i],
];
for (const [label, pattern] of forbiddenFinalVisualPatterns) {
  if (pattern.test(finalVisualSource)) failures.push(`final visual layer reintroduced forbidden ${label}`);
}
for (const match of finalVisualSource.matchAll(/box-shadow\s*:\s*([^;}]+)/gi)) {
  const value = match[1].trim().toLowerCase();
  if (!["none", "initial", "inherit", "unset"].includes(value)) {
    failures.push(`final visual layer reintroduced non-neutral box shadow: ${match[1].trim()}`);
  }
}
const globalAuraDisabled = /body::before\s*(?:,\s*body::after\s*)?\{[^}]*display\s*:\s*none/i.test(adaptiveNative);
if (!globalAuraDisabled) {
  failures.push("decorative global background grid/auras are not explicitly disabled");
}
if (!/\.journey-card::after\s*\{[^}]*display\s*:\s*none/i.test(adaptiveStructures)) {
  failures.push("legacy journey-card glow decoration is not explicitly disabled");
}
const compactSurfaceSelectors = [".detail-link-card", ".journey-card", ".plane-card"];
for (const selector of compactSurfaceSelectors) {
  const escaped = selector.replaceAll(".", "\\.");
  const rule = new RegExp(`${escaped}\\s*\\{[^}]*min-height\\s*:\\s*0`, "i");
  if (!rule.test(adaptiveNative)) failures.push(`compact visual policy missing min-height: 0 for ${selector}`);
}

if (failures.length) {
  console.error("Website quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Website quality gate PASS (${routes.length} routes inspected).`);
