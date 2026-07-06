from datetime import timedelta

from app.core.security import (
    create_access_token,
    verify_access_token,
    _encode_json,
    _sign_jwt,
)


def test_create_access_token_returns_verifiable_payload() -> None:
    token = create_access_token(
        subject="user-123",
        role="participant",
        expires_delta=timedelta(minutes=5),
    )

    payload = verify_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "participant"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_verify_access_token_rejects_tampered_token() -> None:
    token = create_access_token(
        subject="user-123",
        role="participant",
        expires_delta=timedelta(minutes=5),
    )
    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    assert verify_access_token(tampered_token) is None


def test_verify_access_token_rejects_expired_token() -> None:
    token = create_access_token(
        subject="user-123",
        role="participant",
        expires_delta=timedelta(seconds=-1),
    )

    assert verify_access_token(token) is None


def test_verify_access_token_rejects_missing_subject() -> None:
    token = _make_token({"role": "participant", "type": "access", "exp": 4102444800})

    assert verify_access_token(token) is None


def test_verify_access_token_rejects_missing_role() -> None:
    token = _make_token({"sub": "user-123", "type": "access", "exp": 4102444800})

    assert verify_access_token(token) is None


def test_verify_access_token_rejects_invalid_role() -> None:
    token = _make_token(
        {"sub": "user-123", "role": "admin", "type": "access", "exp": 4102444800}
    )

    assert verify_access_token(token) is None


def _make_token(payload: dict[str, object]) -> str:
    signing_input = ".".join(
        [
            _encode_json({"alg": "HS256", "typ": "JWT"}),
            _encode_json(payload),
        ]
    )
    return ".".join([signing_input, _sign_jwt(signing_input)])
