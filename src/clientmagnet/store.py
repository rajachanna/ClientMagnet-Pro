"""Local audit reports, consent-first leads and minimal audit events."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS audits (
                    id TEXT PRIMARY KEY, url TEXT NOT NULL, source TEXT NOT NULL,
                    score INTEGER NOT NULL, data_json TEXT NOT NULL, created_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
                    website TEXT NOT NULL, interest TEXT NOT NULL, consent_utc TEXT NOT NULL,
                    created_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    created_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audits_recent ON audits(created_utc);
                CREATE INDEX IF NOT EXISTS idx_leads_recent ON leads(created_utc);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
        finally:
            db.close()

    def save_audit(self, report: dict):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO audits VALUES (?,?,?,?,?,?)", (
                report["id"], report["url"], report["source"], report["scores"]["overall"],
                json.dumps(report, ensure_ascii=False), report["created_utc"],
            ))
            db.execute("INSERT INTO events VALUES (?,?,?,?)", (
                uuid.uuid4().hex, report["id"], "AUDIT_CREATED", utc_now(),
            ))
            db.execute("COMMIT")

    def get_audit(self, audit_id: str):
        with self.connect() as db:
            row = db.execute("SELECT data_json FROM audits WHERE id=?", (audit_id,)).fetchone()
        return json.loads(row["data_json"]) if row else None

    def list_audits(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,url,source,score,created_utc FROM audits ORDER BY created_utc DESC LIMIT 100"
            )]

    def add_lead(self, *, name, email, website, interest):
        record = {"id": uuid.uuid4().hex, "name": name, "email": email,
                  "website": website, "interest": interest,
                  "created_utc": utc_now(), "consent_utc": utc_now()}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO leads
                (id,name,email,website,interest,consent_utc,created_utc)
                VALUES(:id,:name,:email,:website,:interest,:consent_utc,:created_utc)""", record)
            db.execute("INSERT INTO events VALUES (?,?,?,?)", (
                uuid.uuid4().hex, record["id"], "LEAD_OPTED_IN", utc_now(),
            ))
            db.execute("COMMIT")
        return {"id": record["id"], "received": True}

    def leads(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM leads ORDER BY created_utc DESC LIMIT 100"
            )]

    def stats(self):
        with self.connect() as db:
            return {
                "saved_audits": db.execute("SELECT count(*) FROM audits").fetchone()[0],
                "consenting_leads": db.execute("SELECT count(*) FROM leads").fetchone()[0],
                "audit_events": db.execute("SELECT count(*) FROM events").fetchone()[0],
                "average_local_score": round(db.execute("SELECT avg(score) FROM audits").fetchone()[0] or 0, 1),
            }
