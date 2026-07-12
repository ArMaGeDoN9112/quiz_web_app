from app.core.security import hash_password, verify_password


def test_hash_password_returns_verifiable_hash_without_plaintext() -> None:
    password = "correct horse battery staple"

    password_hash = hash_password(password)

    assert isinstance(password_hash, str)
    assert password_hash != password
    assert password not in password_hash
    assert verify_password(password, password_hash) is True


def test_verify_password_rejects_invalid_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong horse battery staple", password_hash) is False


def test_hash_password_uses_unique_salts() -> None:
    password = "correct horse battery staple"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("correct horse battery staple", "not-a-password-hash") is False
