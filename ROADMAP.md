# ClientMagnet Pro — Honest roadmap

## Shipped v0.1 (local-first prototype)

- FastAPI backend and premium responsive dashboard.
- HTML rule-based checks for page title, meta description, H1, canonical, indexability, links, language, viewport, image alt, form labels, heading hierarchy, new tabs, CTAs and contact routes.
- 0–100 weighted **internal diagnostic score** and concrete recommendations with inline evidence.
- A public synthetic audit and a freely downloadable **example PDF**.
- Authorized private HTML audit with stored history and generated PDF reports.
- Opt-in lead capture with consent-required validation, local audit records and operator-only lead list.
- Optional HTTPS fetch implementation with global-IP pinning and bounded reads, disabled by default.
- Docker / Compose, offline demo, unit/integration tests and GitHub Actions workflow.

## Next — engineering and commercial readiness

1. Verify live scan against real client-authorized HTTPS websites inside a locked-down egress sandbox.
2. Integrate Google PageSpeed Insights / Lighthouse **as separately measured metrics**, not rebranded heuristic scores.
3. Add crawl budget, robots/site rules, safe sitemap ingestion and multi-page comparisons after security review.
4. Add accounts, protected shared public reports, CAPTCHA, multi-worker rate limits, approval/consent deletion and data retention tools.
5. Integrate Google Analytics/Search Console **only with customers' explicit authorization**.
6. Add real opt-in CRM/email workflows using provider sandbox and delivery receipts; never auto-spam.
7. Deploy production-ready HTTPS application and instrument conversion funnel, inbound lead quality and referral sources.
8. Collect customer-approved before/after case studies demonstrating measurable improvements.

No hosted demo, live customers, website performance ranking, real conversions or paid clients are claimed by the prototype.
