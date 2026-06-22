# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This repository hosts the **MENTORFY** marketing landing page. MENTORFY is an AI platform that
clones a creator's knowledge into a personal AI mentor — one that thinks like the creator (their
beliefs, thinking patterns, and decision-making), gives every student their own persistent memory,
and is available 24/7. Creators clone their mentor, manage it from a dashboard, and share private
mentor links; students log in to access mentors built on creators' knowledge.

## Structure

The site is intentionally a **single self-contained file** — there is no build step, framework, or
package manager.

- `index.html` — the complete landing page. All CSS lives in one `<style>` block and all JS in one
  `<script>` block at the end of the file. Sections are top-to-bottom: nav, hero (with chat mockup),
  trusted strip, problem, solution, features, how-it-works, audience split, testimonials, pricing,
  FAQ, closing CTA, footer.
- `assets/logo.png` — brand logo, used as-is. Never recreate or redraw the logo.
- `README.md` — preview and deploy instructions.

## Commands

- **Preview locally:** `python3 -m http.server 8000` then open `http://localhost:8000`
  (or just open `index.html` in a browser).
- **Build / tests / lint:** none — this is plain static HTML/CSS/JS.

## Conventions

- **Design tokens** are CSS custom properties on `:root` in `index.html` (palette, radius, easing).
  Change colors/spacing there rather than hardcoding values in rules. The brand palette is
  orange-on-black: gradient `#ff3d00 → #ff6a00 → #ff9d2f` (`--grad`) on a near-black base.
- **Fonts:** Space Grotesk (headings) + Inter (body), loaded from Google Fonts in `<head>`.
- **Icons** are inline SVG (no icon library) to keep the file dependency-free.
- **Animation:** scroll-reveal uses a single IntersectionObserver on `.reveal` elements; honor
  `prefers-reduced-motion` (already handled in CSS) when adding motion.
- **No browser storage** and **no backend** — the email form is front-end only (validate + confirm).
- Keep everything in `index.html`; only split into multiple files if the page genuinely outgrows
  a single file.

## Branch

Active development branch: `claude/claude-md-docs-BTDWz`. Do not push to other branches without
explicit permission, and do not open a pull request unless asked.
