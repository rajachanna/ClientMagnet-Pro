"""Validated configuration with safe defaults."""
from dataclasses import dataclass
from pathlib import Path
import os


def flag(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("data/clientmagnet.sqlite")
    business_name: str = "NextGen Tech Solutions"
    operator_key: str = ""
    public_scans_enabled: bool = False
    live_fetch_enabled: bool = False
    public_leads_enabled: bool = True
    max_requests_per_hour: int = 5

    @classmethod
    def from_env(cls):
        g = os.environ.get
        return cls(
            db_path=Path(g("CM_DB_PATH", "data/clientmagnet.sqlite")),
            business_name=g("CM_BUSINESS_NAME", "NextGen Tech Solutions"),
            operator_key=g("CM_OPERATOR_KEY", ""),
            public_scans_enabled=flag(g("CM_PUBLIC_SCANS_ENABLED", "false")),
            live_fetch_enabled=flag(g("CM_LIVE_FETCH_ENABLED", "false")),
            public_leads_enabled=flag(g("CM_PUBLIC_LEADS_ENABLED", "true")),
            max_requests_per_hour=int(g("CM_MAX_REQUESTS_PER_HOUR", "5")),
        )

    @property
    def operator_ready(self) -> bool:
        return len(self.operator_key) >= 32 and not self.operator_key.startswith("REPLACE_")

    def validate(self) -> None:
        if not 1 <= len(self.business_name) <= 100:
            raise ValueError("Business name must have 1–100 characters")
        if not 1 <= self.max_requests_per_hour <= 60:
            raise ValueError("Request limit must be between 1 and 60")
        if self.public_scans_enabled and not self.live_fetch_enabled:
            raise ValueError("Public scans require live fetch to be deliberately enabled")
