import type { MetadataRoute } from "next";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";
const paths = ["", "/about", "/platform", "/security", "/contact", "/privacy", "/terms"];
export default function sitemap(): MetadataRoute.Sitemap { return paths.map((path) => ({ url: `${siteUrl}${path}`, changeFrequency: path === "" ? "weekly" : "monthly", priority: path === "" ? 1 : 0.7 })); }
