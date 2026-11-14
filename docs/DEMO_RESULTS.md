# ClientMagnet Pro — Local demonstration evidence

Date: 2026-11-14 · Version: 0.1.0 · Environment: local/offline.

- Python pytest suite: **56 passed**.
- Offline example website audit: **15 HTML checks**, diagnostic score **93/100**.
- Private operator HTML audit: generated and persisted.
- Report PDF: **3.3 KB**, valid PDF header and visually inspected rendered page.
- Lead submission without explicit consent: **HTTP 422**.
- Consented synthetic lead request: **HTTP 201**.
- Unconfigured public live scan: **HTTP 403**, fail-closed by default.
- Generated Python wheel: verified dashboard HTML asset included.
- Dashboard preview: Chromium rendering of local HTML with the application's **synthetic sample audit data**; screenshot **is not a hosted service or live traffic evidence**.

All records used in the offline demo are fabricated. No real customer, marketing outreach, search ranking, Google PageSpeed score or production deployment was observed.

Run independently:

```bash
pip install -e '.[dev]'
python -m pytest -q
python scripts/demo.py
```
