# MENTORFY — Landing Page

A single-page marketing site for **MENTORFY**, the AI platform that lets creators clone their
knowledge into a personal AI mentor — an AI that thinks like the creator (their beliefs, frameworks,
and decision patterns), remembers every student individually, and is available 24/7.

## What's here

- `index.html` — the entire landing page (HTML, CSS, and JS inline; no build step).
- `assets/logo.png` — the MENTORFY brand logo (used as-is, never recreated).

## Preview

Open `index.html` directly in a browser, or serve the folder locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Deploy (GitHub Pages)

1. Push to GitHub.
2. Repo **Settings → Pages → Build and deployment → Source: Deploy from a branch**.
3. Select the branch and `/ (root)`, then save. The site publishes at the Pages URL.

Any static host works too (Netlify, Vercel, Cloudflare Pages) — just point it at the repo root.

## Design

- **Palette:** orange-on-black (`#ff3d00 → #ff6a00 → #ff9d2f` gradient on a near-black `#0a0a0b` base).
- **Type:** Space Grotesk (headings) + Inter (body) via Google Fonts.
- **Motion:** scroll-reveal via IntersectionObserver, FAQ accordion, sticky/blur nav. Respects
  `prefers-reduced-motion`.

## Notes

- The email capture is front-end only (no backend) — it validates and shows a confirmation message.
- Pricing numbers are indicative placeholders for early access.
- For a tighter inline logo lockup, a transparent-background cut of just the "M" mark would help;
  the current square logo is used as a rounded app-icon-style badge.
