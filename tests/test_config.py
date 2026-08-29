from __future__ import annotations

from dataclasses import replace

import pytest

from reviewdesk.config import Settings


def test_production_requires_strong_separate_tokens(settings: Settings) -> None:
    with pytest.raises(ValueError, match="ADMIN_TOKEN"):
        replace(settings, app_env="production", admin_token="change-me").validate()
    with pytest.raises(ValueError, match="different"):
        replace(
            settings,
            app_env="production",
            admin_token="a-long-production-token-123456",
            webhook_token="a-long-production-token-123456",
        ).validate()


def test_smtp_requires_host(settings: Settings) -> None:
    with pytest.raises(ValueError, match="SMTP_HOST"):
        replace(settings, email_provider="smtp", smtp_host="").validate()

