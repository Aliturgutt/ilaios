import type { MetadataRoute } from "next";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";
const paths = ["", "/about", "/platform", "/platform/control-plane", "/platform/execution", "/platform/evidence", "/security", "/security/permissions", "/security/approvals", "/security/audit", "/contact", "/privacy", "/terms"];
export default function sitemap(): MetadataRoute.Sitemap { return paths.map((path) => ({ url: `${siteUrl}${path}`, changeFrequency: path === "" ? "weekly" : "monthly", priority: path === "" ? 1 : path.split("/").length > 2 ? 0.6 : 0.7 })); }
