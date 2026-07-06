import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_requires_jwt_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_short_jwt_secret_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key="too-short")
