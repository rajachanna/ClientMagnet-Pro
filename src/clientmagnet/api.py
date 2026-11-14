"""FastAPI website audit and opt-in lead capture app.

Safe defaults: public live scans off; operator-controlled sample/HTML audits on;
no automatic outbound emails, scraping campaigns or marketing sends.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
from hmac import compare_digest
from pathlib import Path
from threading import Lock
from time import monotonic
import re
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response

from . import __version__
from .audit import audit_page
from .config import Settings
from .fetch import FetchError, fetch_html, validate_url
from .models import LeadIn, OperatorAuditIn, PublicAuditIn
from .reports import pdf_bytes
from .sample import SAMPLE_HTML, SAMPLE_URL
from .store import Store


class RateLimit:
    def __init__(self, max_events: int, window_seconds: int = 3600):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self.events = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()
        with self.lock:
            q = self.events[key]
            while q and q[0] <= now - self.window_seconds:
                q.popleft()
            if len(q) >= self.max_events:
                return False
            q.append(now)
            return True


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    app = FastAPI(title="ClientMagnet Pro | Website Audit & Leads", version=__version__)
    store: Store | None = None
    limiter = RateLimit(settings.max_requests_per_hour)

    def get_store() -> Store:
        nonlocal store
        if store is None:
            store = Store(settings.db_path)
        return store

    def require_operator(x_operator_key: str | None = Header(default=None)) -> None:
        if not settings.operator_ready or not x_operator_key or not compare_digest(settings.operator_key, x_operator_key):
            raise HTTPException(401, "Valid operator key required")

    def requester(request: Request, channel: str) -> str:
        # Intentionally ignores X-Forwarded-For, which is user-controlled unless
        # a trusted reverse proxy sanitizes it. In production use proxy-aware IP rules.
        return channel + ":" + (request.client.host if request.client else "unknown")

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(Path(__file__).parent / "static" / "index.html",
                            headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        return {
            "status": "ok", "version": __version__,
            "live_fetch_enabled": settings.live_fetch_enabled,
            "public_scans_enabled": settings.public_scans_enabled,
            "public_leads_enabled": settings.public_leads_enabled,
            "mode": "LOCAL_PROTOTYPE",
        }

    @app.get("/api/demo")
    def public_demo():
        return audit_page(SAMPLE_URL, SAMPLE_HTML, source="synthetic_sample")

    @app.get("/api/demo/pdf")
    def public_sample_pdf():
        report = audit_page(SAMPLE_URL, SAMPLE_HTML, source="synthetic_sample")
        return Response(content=pdf_bytes(report, settings.business_name), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="example-website-audit.pdf"'})

    @app.post("/api/operator/audits", dependencies=[Depends(require_operator)])
    def operator_audit(req: OperatorAuditIn):
        try:
            url = validate_url(req.url)
            if req.html is None:
                if not settings.live_fetch_enabled:
                    raise HTTPException(403, "Live website fetching is disabled; submit HTML or explicitly configure live mode")
                fetched = fetch_html(url)
                report = audit_page(fetched.url, fetched.html, source="live_https", fetch_ms=fetched.elapsed_ms)
            else:
                report = audit_page(url, req.html, source="operator_submitted_html")
        except FetchError as exc:
            raise HTTPException(422, str(exc)) from exc
        get_store().save_audit(report)
        return report

    @app.post("/api/public/audit")
    def public_audit(req: PublicAuditIn, request: Request):
        if not settings.public_scans_enabled:
            raise HTTPException(403, "Public live audits are disabled. Use the synthetic demo.")
        if not limiter.allow(requester(request, "audit")):
            raise HTTPException(429, "Public scan limit reached. Try later.")
        try:
            normalized = validate_url(req.url)
            page = fetch_html(normalized)
            report = audit_page(page.url, page.html, source="live_https", fetch_ms=page.elapsed_ms)
        except FetchError as exc:
            raise HTTPException(422, str(exc)) from exc
        get_store().save_audit(report)
        return report

    @app.post("/api/leads", status_code=201)
    def submit_lead(req: LeadIn, request: Request):
        if not settings.public_leads_enabled:
            raise HTTPException(403, "Lead capture disabled")
        if not req.consent:
            raise HTTPException(422, "Explicit consent required before storing a request")
        if req.website:
            try:
                website = validate_url(req.website)
            except FetchError as exc:
                raise HTTPException(422, str(exc)) from exc
        else:
            website = ""
        if not limiter.allow(requester(request, "lead")):
            raise HTTPException(429, "Too many lead requests. Try later.")
        return get_store().add_lead(name=req.name, email=req.email, website=website, interest=req.interest)

    @app.get("/api/operator/audits", dependencies=[Depends(require_operator)])
    def audit_history():
        return {"audits": get_store().list_audits()}

    @app.get("/api/operator/audits/{report_id}", dependencies=[Depends(require_operator)])
    def get_report(report_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", report_id):
            raise HTTPException(404, "Audit not found")
        item = get_store().get_audit(report_id)
        if item is None:
            raise HTTPException(404, "Audit not found")
        return item

    @app.get("/api/operator/audits/{report_id}/pdf", dependencies=[Depends(require_operator)])
    def report_pdf(report_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", report_id):
            raise HTTPException(404, "Audit not found")
        item = get_store().get_audit(report_id)
        if item is None:
            raise HTTPException(404, "Audit not found")
        return Response(content=pdf_bytes(item, settings.business_name), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="clientmagnet-{report_id}.pdf"'})

    @app.get("/api/operator/leads", dependencies=[Depends(require_operator)])
    def leads():
        return {"leads": get_store().leads()}

    @app.get("/api/operator/metrics", dependencies=[Depends(require_operator)])
    def metrics():
        return get_store().stats()

    return app


app = create_app()
