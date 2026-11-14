"""Strict HTTP request payloads; no automatic marketing delivery."""
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class OperatorAuditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=12, max_length=750)
    html: str | None = Field(default=None, max_length=750000)


class PublicAuditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=12, max_length=750)


class LeadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    website: str = Field(default="", max_length=750)
    interest: str = Field(default="website audit consultation", max_length=160)
    consent: bool

    @field_validator("name", "interest")
    @classmethod
    def normalize(cls, value):
        text = " ".join(value.split())
        if not text or any(ord(ch) < 32 for ch in text):
            raise ValueError("Invalid text")
        return text

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+", value):
            raise ValueError("Invalid email address")
        return value
