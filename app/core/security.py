import base64
import binascii
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16
PASSWORD_HASH_SCHEME = "scrypt"


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
