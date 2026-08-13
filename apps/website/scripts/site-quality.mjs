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
const requiredPublicMailboxes = [
  "contact@ilaios.com",
  "info@ilaios.com",
  "support@ilaios.com",
  "privacy@ilaios.com",
  "security@ilaios.com",
  "abuse@ilaios.com",
];
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
const source = (await Promise.all(files.map(async file => `${file}\n${await readFile(file, "utf8")}`))).join("\n");
const failures = [];

for (const mailbox of forbiddenPublicMailboxes) {
  if (source.includes(`mailto:${mailbox}`)) failures.push(`forbidden public mailbox exposed: ${mailbox}`);
}
for (const mailbox of requiredPublicMailboxes) {
  if (!source.includes(`mailto:${mailbox}`)) failures.push(`required public mailbox missing: ${mailbox}`);
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

if (failures.length) {
  console.error("Website quality gate FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Website quality gate PASS (${routes.length} routes inspected).`);
