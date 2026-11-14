"""Transparent, deterministic, one-page website audit.

No fake Lighthouse scores, no hidden LLM guesswork, no performance claim based
on HTML alone.  This is a rule-based diagnostic of the retrieved HTML snapshot.
"""
from datetime import datetime, timezone
from html import unescape
from uuid import uuid4
from bs4 import BeautifulSoup
import re

from .fetch import validate_url

CTA = re.compile(r"\b(contact|book|schedule|request|quote|consult|call us|get started|start now|free audit|talk to|demo)\b", re.I)


def audit_page(url: str, html: str, *, source: str = "submitted_html", fetch_ms: int | None = None) -> dict:
    normalized = validate_url(url)
    if len(html.encode("utf-8")) > 750_000:
        raise ValueError("HTML exceeds safe 750 KB limit")
    soup = BeautifulSoup(html, "html.parser")
    document_title = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
    metas = soup.find_all("meta")
    description = next((x.get("content", "").strip() for x in metas if x.get("name", "").lower() == "description"), "")
    viewport = next((x.get("content", "") for x in metas if x.get("name", "").lower() == "viewport"), "")
    robots = next((x.get("content", "") for x in metas if x.get("name", "").lower() == "robots"), "")
    headings = [x.name for x in soup.find_all(re.compile(r"^h[1-6]$"))]
    h1s = soup.find_all("h1")
    html_root = soup.find("html")
    lang = (html_root.get("lang", "") if html_root else "").strip()
    images = soup.find_all("img")
    missing_alts = [img for img in images if img.get("alt") is None]
    forms = soup.find_all("form")
    unlabeled_fields = []
    for field in soup.select("input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select"):
        if field.get("type", "").lower() in ("checkbox", "radio") and field.find_parent("label"):
            continue
        field_id = field.get("id", "")
        named_label = bool(field_id and soup.find("label", attrs={"for": field_id}))
        if not (named_label or field.find_parent("label") or field.get("aria-label") or field.get("aria-labelledby") or field.get("title")):
            unlabeled_fields.append(field)
    anchors = soup.find_all("a", href=True)
    links = [a for a in anchors if a.get("href", "").strip() and not a.get("href", "").lower().startswith(("#", "javascript:"))]
    cta_links = [a for a in anchors if CTA.search(a.get_text(" ", strip=True) + " " + a.get("aria-label", ""))]
    contact = any("contact" in (a.get("href", "").lower() + a.get_text(" ", strip=True).lower()) for a in anchors)
    email_or_phone = any(a.get("href", "").lower().startswith(("mailto:", "tel:")) for a in anchors)
    insecure_new_tabs = [a for a in anchors if a.get("target", "").lower() == "_blank"
                         and not {"noopener", "noreferrer"}.intersection(set(a.get("rel", [])))]
    heading_jumps = 0
    for prev, current in zip(headings, headings[1:]):
        if int(current[1]) - int(prev[1]) > 1:
            heading_jumps += 1
    checks = []

    def check(key, label, category, ok, evidence, recommendation, weight=1, warning=False):
        status = "pass" if ok else "warning" if warning else "fail"
        checks.append({
            "key": key, "label": label, "category": category,
            "status": status, "weight": weight,
            "evidence": str(evidence)[:250],
            "recommendation": "" if ok else recommendation,
        })

    check("title", "Descriptive page title", "seo", 15 <= len(document_title) <= 65,
          f"Title length: {len(document_title)} characters", "Write a unique 15–65 character page title.", 3)
    check("description", "Search snippet description", "seo", 70 <= len(description) <= 170,
          f"Meta description length: {len(description)} characters", "Add a clear 70–170 character meta description.", 2)
    check("h1", "Exactly one main heading", "seo", len(h1s) == 1,
          f"H1 headings: {len(h1s)}", "Use one descriptive H1 heading on the page.", 2)
    check("canonical", "Canonical URL declared", "seo",
          bool(soup.find("link", rel=lambda x: x and "canonical" in x)),
          "Canonical link present" if soup.find("link", rel=lambda x: x and "canonical" in x) else "No canonical link found",
          "Add a valid canonical link after checking the preferred URL.", 1, warning=True)
    check("robots", "Page not explicitly noindexed", "seo", "noindex" not in robots.lower(),
          "Robots: " + (robots[:90] or "not specified"), "Remove noindex only if this page should appear in search.", 3)
    check("links", "Navigable links available", "seo", len(links) >= 2,
          f"Navigable link count: {len(links)}", "Add meaningful navigation and contextual internal links.", 1, warning=True)
    check("lang", "Document language set", "accessibility", bool(re.fullmatch(r"[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*", lang)),
          "HTML lang: " + (lang or "missing"), "Set the HTML lang attribute to the actual language.", 2)
    check("viewport", "Mobile viewport meta", "accessibility", "width=device-width" in viewport.lower(),
          "Viewport: " + (viewport[:90] or "missing"), "Add a device-width viewport meta tag.", 3)
    check("alts", "Images have alt attributes", "accessibility", not missing_alts,
          f"Missing alt attributes: {len(missing_alts)} / {len(images)} images",
          "Add meaningful alt descriptions, or alt=\"\" to truly decorative images.", 2)
    check("labels", "Form inputs have accessible labels", "accessibility", not unlabeled_fields,
          f"Unlabeled fields: {len(unlabeled_fields)}", "Add label/for, enclosing label or aria-label to every field.", 3)
    check("headings", "Heading hierarchy is consistent", "accessibility", not heading_jumps,
          f"Heading-level jumps: {heading_jumps}", "Avoid skipping heading levels (e.g. H2 directly to H4).", 1, warning=True)
    check("cta", "Visible conversion call-to-action", "conversion", bool(cta_links),
          f"Relevant CTA links: {len(cta_links)}", "Add a clear, visible contact/book/quote call-to-action.", 3)
    check("contact", "Contact route is discoverable", "conversion", contact or email_or_phone,
          f"Contact link: {contact}; email/phone link: {email_or_phone}", "Add a prominent contact page, phone or email link.", 2)
    check("form", "Contact or lead form exists", "conversion", bool(forms),
          f"HTML forms: {len(forms)}", "Consider a simple accessible inquiry form if appropriate for your business.", 1, warning=True)
    check("new_tabs", "New-tab links use safe rel", "accessibility", not insecure_new_tabs,
          f"Unsafe target=_blank links: {len(insecure_new_tabs)}", "Use rel=noopener noreferrer on external new-tab links.", 1, warning=True)

    categories = {}
    for category in ("seo", "accessibility", "conversion"):
        subset = [x for x in checks if x["category"] == category]
        denom = sum(x["weight"] for x in subset)
        num = sum(x["weight"] * (1 if x["status"] == "pass" else .5 if x["status"] == "warning" else 0) for x in subset)
        categories[category] = round(100 * num / denom) if denom else 0
    overall = round(.4 * categories["seo"] + .35 * categories["accessibility"] + .25 * categories["conversion"])
    misses = sorted([c for c in checks if c["status"] != "pass"], key=lambda c: (c["status"] != "fail", -c["weight"], c["key"]))
    return {
        "id": uuid4().hex,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "url": normalized,
        "source": source,
        "title": document_title[:180],
        "scores": {"overall": overall, **categories},
        "checks": checks,
        "priority_recommendations": [{"title": c["label"], "recommendation": c["recommendation"], "evidence": c["evidence"]} for c in misses[:5]],
        "summary": {
            "passed": sum(c["status"] == "pass" for c in checks),
            "failed": sum(c["status"] == "fail" for c in checks),
            "warnings": sum(c["status"] == "warning" for c in checks),
            "total": len(checks),
            "images": len(images),
            "links": len(links),
        },
        "timing": {"measured_fetch_ms": fetch_ms} if fetch_ms is not None else {"measured_fetch_ms": None},
        "limitations": (
            "One-page HTML heuristics only. Scores are internally weighted diagnostic scores, NOT Lighthouse, Google SEO ranking, "
            "Core Web Vitals, UX testing, mobile emulation, penetration testing, accessibility certification, "
            "or measured conversion rates. This report does not prove business results."
        ),
    }
