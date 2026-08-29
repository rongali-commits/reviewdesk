from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reviewdesk.app import create_app
from reviewdesk.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    root = Path(__file__).resolve().parents[1]
    business_file = tmp_path / "business.json"
    sequence_file = tmp_path / "sequence.json"
    business_file.write_text(
        (root / "data" / "business.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sequence_file.write_text(
        (root / "data" / "sequence.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return Settings(
        app_env="test",
        admin_token="test-admin-token-that-is-private",
        webhook_token="test-webhook-token-that-is-private",
        database_path=tmp_path / "reviewdesk.db",
        business_file=business_file,
        sequence_file=sequence_file,
        email_provider="demo",
        smtp_host="",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        smtp_use_tls=True,
        request_worker_enabled=False,
        request_poll_seconds=60,
        request_rate_limit_per_minute=20,
        seed_demo_data=False,
        public_base_url="https://reviews.example.com",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(settings: Settings) -> dict[str, str]:
    return {"X-Admin-Token": settings.admin_token}


@pytest.fixture
def webhook_headers(settings: Settings) -> dict[str, str]:
    return {"X-Webhook-Token": settings.webhook_token}


@pytest.fixture
def contact_payload() -> dict[str, object]:
    return {
        "name": "Taylor Morgan",
        "email": "taylor@example.com",
        "phone": "",
        "service": "Annual maintenance",
        "service_date": "2026-08-28",
        "source": "test",
        "reminders_enabled": True,
        "website": "",
    }
