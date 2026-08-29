from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bundled(name: str) -> Path:
    packaged = Path(__file__).parent / "defaults" / name
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "data" / name


@dataclass(frozen=True)
class Settings:
    app_env: str
    admin_token: str
    webhook_token: str
    database_path: Path
    business_file: Path
    sequence_file: Path
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    request_worker_enabled: bool
    request_poll_seconds: int
    request_rate_limit_per_minute: int
    seed_demo_data: bool
    public_base_url: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        default_database_path = (
            "/tmp/reviewdesk.db" if _bool(os.getenv("VERCEL"), False) else "runtime/reviewdesk.db"
        )
        return cls(
            app_env=os.getenv("APP_ENV", "development").strip().lower(),
            admin_token=os.getenv("ADMIN_TOKEN", "development-admin-token"),
            webhook_token=os.getenv("WEBHOOK_TOKEN", "development-webhook-token"),
            database_path=Path(os.getenv("DATABASE_PATH", default_database_path)),
            business_file=Path(os.getenv("BUSINESS_FILE", str(_bundled("business.json")))),
            sequence_file=Path(os.getenv("SEQUENCE_FILE", str(_bundled("sequence.json")))),
            email_provider=os.getenv("EMAIL_PROVIDER", "demo").strip().lower(),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_tls=_bool(os.getenv("SMTP_USE_TLS"), True),
            request_worker_enabled=_bool(os.getenv("REQUEST_WORKER_ENABLED"), True),
            request_poll_seconds=max(15, int(os.getenv("REQUEST_POLL_SECONDS", "60"))),
            request_rate_limit_per_minute=max(
                1, int(os.getenv("REQUEST_RATE_LIMIT_PER_MINUTE", "10"))
            ),
            seed_demo_data=_bool(os.getenv("SEED_DEMO_DATA"), True),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        )

    def validate(self) -> None:
        if self.email_provider not in {"demo", "smtp"}:
            raise ValueError("EMAIL_PROVIDER must be demo or smtp")
        if self.email_provider == "smtp" and not self.smtp_host:
            raise ValueError("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
        if not self.public_base_url.startswith(("https://", "http://")):
            raise ValueError("PUBLIC_BASE_URL must begin with https:// or http://")
        if self.app_env == "production":
            weak = {
                "development-admin-token",
                "development-webhook-token",
                "change-me",
                "",
            }
            if self.admin_token in weak or len(self.admin_token) < 24:
                raise ValueError("Set a strong ADMIN_TOKEN in production")
            if self.webhook_token in weak or len(self.webhook_token) < 24:
                raise ValueError("Set a strong WEBHOOK_TOKEN in production")
            if self.admin_token == self.webhook_token:
                raise ValueError("ADMIN_TOKEN and WEBHOOK_TOKEN must be different")

    def load_business(self) -> dict[str, Any]:
        return json.loads(self.business_file.read_text(encoding="utf-8"))

    def load_sequence(self) -> list[dict[str, Any]]:
        return json.loads(self.sequence_file.read_text(encoding="utf-8"))
