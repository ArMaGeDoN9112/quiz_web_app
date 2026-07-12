import base64
import binascii
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.models import UserRole

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16
PASSWORD_HASH_SCHEME = "scrypt"
JWT_ALGORITHM = "HS256"
JWT_TYPE = "JWT"
ACCESS_TOKEN_TYPE = "access"
JWT_ROLES = {role.value for role in UserRole}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)

    return "$".join(
        [
            PASSWORD_HASH_SCHEME,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode_bytes(salt),
            _encode_bytes(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, n_value, r_value, p_value, salt_value, digest_value = password_hash.split(
            "$"
        )
        if scheme != PASSWORD_HASH_SCHEME:
            return False

        n = int(n_value)
        r = int(r_value)
        p = int(p_value)
        if (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False

        salt = _decode_bytes(salt_value)
        expected_digest = _decode_bytes(digest_value)
        actual_digest = _scrypt(password, salt, n, r, p)
    except (binascii.Error, ValueError, TypeError):
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    header = {"alg": JWT_ALGORITHM, "typ": JWT_TYPE}
    payload = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "exp": int(expires_at.timestamp()),
    }
    signing_input = ".".join([_encode_json(header), _encode_json(payload)])
    signature = _sign_jwt(signing_input)
    return ".".join([signing_input, signature])


def verify_access_token(token: str) -> dict[str, Any] | None:
    try:
        header_value, payload_value, signature = token.split(".")
        signing_input = ".".join([header_value, payload_value])
        if not hmac.compare_digest(signature, _sign_jwt(signing_input)):
            return None

        header = _decode_json(header_value)
        payload = _decode_json(payload_value)
        if header.get("alg") != JWT_ALGORITHM or header.get("typ") != JWT_TYPE:
            return None
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            return None
        if payload.get("role") not in JWT_ROLES:
            return None
        if int(payload["exp"]) <= int(datetime.now(UTC).timestamp()):
            return None
    except (binascii.Error, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    return payload


def _scrypt(password: str, salt: bytes, n_value: int, r_value: int, p_value: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_value,
        r=r_value,
        p=p_value,
        dklen=SCRYPT_DKLEN,
    )


def _encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _encode_json(value: dict[str, Any]) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _encode_bytes(payload)


def _decode_json(value: str) -> dict[str, Any]:
    decoded = _decode_bytes(value)
    payload = json.loads(decoded)
    if not isinstance(payload, dict):
        raise ValueError("JWT payload must be an object")
    return payload


def _sign_jwt(signing_input: str) -> str:
    digest = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _encode_bytes(digest)
