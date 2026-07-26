# Portfolio Sites

Two self-contained portfolio websites for Daniel Yoon (AI implementation consulting), each a single `index.html` with all fonts, styles, and JS inlined — zero external requests at runtime.

| Site | Live URL | Guide |
|------|----------|-------|
| 01 — Flagship studio ("the brand") | https://daniel-yoon-ai-implementation-studio-cd-873bf09417.netlify.app | `/#/guide` |
| 02 — The Yoon Lab ("the proof") | https://the-yoon-lab-ai-in-action-cd-37e661397a.netlify.app | `/#/guide` |

## Building

Each site assembles `index.html` from `src.html` (markup + CSS) and `app.js`, inlining base64 font subsets from `_assets/fonts/`:

```bash
cd sites/01-flagship && node build.js
cd sites/02-showcase && node build.js   # SITE1_URL env overrides the cross-link
```

`SITE2_URL` / `SITE1_URL` environment variables control the cross-links between the two sites.

## Deploying

Deployed via the Netlify MCP design-import tool, fed the GitHub **raw** URL of each built `index.html` (the importer needs a URL that serves the raw bundle). `claude_design_project_id` values `dy-flagship-01` / `dy-lab-02` update the existing Netlify sites in place.

Note: these are single-file deploys with no server-side redirects, so the guide routes are hash-canonical (`/#/guide`); each site's router also handles path-based `/guide` in-page.

## Architecture notes

- **01-flagship** — cinematic dark editorial site. Hand-rolled WebGL particle engine (no libraries): ~14k points morphing between seven generated forms, scroll-driven, with per-shape rotation modes and per-section offset/dim. Instrument Serif / Instrument Sans / Fragment Mono.
- **02-showcase** — Swiss-tactile light "lab" with three working demos: a scripted booking chatbot (intent matcher + multi-step flow), a live-ticking canvas dashboard (crosshair tooltips, target reference line, AI narration), and a personal-CRM demo (warmth scoring, stage pipeline, typewriter-drafted follow-ups). Bricolage Grotesque / Archivo / Spline Sans Mono; chart colors from a validated data-viz palette.
- Both honor `prefers-reduced-motion`, ship OG tags + inline SVG favicons, and were iterated through 3 screenshot-review passes at 3 viewports (Playwright, headless Chromium).
