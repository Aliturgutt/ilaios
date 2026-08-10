import type { MetadataRoute } from "next";
const siteUrl=process.env.NEXT_PUBLIC_SITE_URL??"https://ilaios.com";
const en=["","/about","/platform","/platform/control-plane","/platform/execution","/platform/evidence","/security","/security/permissions","/security/approvals","/security/audit","/contact","/privacy","/terms"];
const tr=["/tr","/tr/about","/tr/platform","/tr/platform/control-plane","/tr/platform/execution","/tr/platform/evidence","/tr/security","/tr/security/permissions","/tr/security/approvals","/tr/security/audit","/tr/contact","/tr/privacy","/tr/terms"];
export default function sitemap():MetadataRoute.Sitemap{return [...en,...tr].map(path=>({url:`${siteUrl}${path}`,changeFrequency:path===""||path==="/tr"?"weekly":"monthly",priority:path===""||path==="/tr"?1:path.split("/").length>2?.6:.7}))}
