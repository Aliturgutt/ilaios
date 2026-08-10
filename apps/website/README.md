# ILAIOS Corporate Website

Public corporate website for ILAIOS. This application is intentionally separate from `apps/web`, which contains product/control-center runtime code.

## Local development

```bash
npm install
npm run dev
```

## Quality gates

```bash
npm run lint
npm run typecheck
npm run build
```

## Deployment

Designed for Vercel. Set `NEXT_PUBLIC_SITE_URL` to the canonical production origin before production deployment.
