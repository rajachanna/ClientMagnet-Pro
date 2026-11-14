# Security and privacy — required reading

**This repository is a local-first engineering prototype, not a production-grade public website crawler or SaaS product.**

## Defensive defaults

- Public live HTTPS audit is **OFF** by default. Operator live HTTPS fetch is also **OFF**. Only the synthetic sample is public without external requests.
- Operator audit, PDF, lead list and metrics require a **strong random API key** supplied in `X-Operator-Key`. Default placeholder keys are rejected. Do not paste keys into public screenshots, URLs or version control.
- When explicitly enabled, the network fetch requires a standard-port HTTPS URL, no credentials or fragments, a public DNS hostname resolving **only to global IP addresses**, pins the validated IP for its TLS socket, uses normal certificate verification, limits HTML to 750 KB, follows at most 2 validated redirects and disallows non-HTML responses.
- This reduces but does not eliminate SSRF, DNS rebinding, network, HTML parsing and resource-exhaustion risks. **Require an outbound firewall** denying metadata services, RFC1918, loopback, link-local, IPv6 ULA, internal DNS, all unusual ports and all egress except safe HTTP(S); create rate limits tied to real users and audit logs and deploy from a sandbox. Do not rely on Python URL filtering as a production security boundary.
- The public lead form requires explicit consent and has a small in-memory per-IP rate limiter. In a multi-worker environment this limiter is **per process**, not global. Add CAPTCHA/honeypot, a shared rate limit, privacy disclosures, monitoring, deletion, consent records and opt-out before operating publicly.
- Lead contact data is stored only in local SQLite in the prototype. No email marketing or unsolicited outreach is ever sent automatically. Restrict backups, encrypt storage, establish a retention/deletion policy and use approved CRM integrations with opt-in.
- Raw submitted HTML is parsed only for diagnostics, **not stored** or rendered in the dashboard; report evidence and labels use `textContent` in JavaScript. Always verify server-side output encoding if adding a public HTML templating system.
- Security tests are **not** a production penetration test. No legal permission to crawl arbitrary sites is implied. Enforce robots/site policies, per-target throttles and customer permission where required.
- The example business and demo results are **fictional** and cannot be used as customer testimonials or performance claims.
- No Lighthouse, Google ranking, real user monitoring or Core Web Vitals scoring is included. Scores are transparent HTML heuristics.

## Production launch gate

1. Secure a dedicated subdomain and HTTPS reverse proxy; rate-limit POST endpoints and outbound requests.
2. Restrict egress using host-level/cloud networking; deploy network fetch in a disposable isolated sandbox with an approved destination allowlist if possible.
3. Provide a public privacy policy, consent withdrawal and deletion workflow; comply with applicable marketing and consumer privacy laws.
4. Set a unique operator key in a protected secret store, rotate credentials, add per-user access controls and harden database access.
5. Implement a queue, bounded concurrency, retries and human-visible errors for third-party fetch failures.
6. Run a real authorized-site test; inspect PDF output, LCP/CLS/INP separately via real performance tools; don't make ranking or traffic claims from these heuristics.
7. Link to public landing page, enable website analytics with privacy controls and publish evidence-based case studies.

Report security concerns privately through https://nextgentechdev.com. Do not disclose real contact data in public issues.
