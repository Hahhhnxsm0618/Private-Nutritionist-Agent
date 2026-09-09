from datetime import UTC, datetime

import pytest
from jwt import InvalidTokenError

from app.auth.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import Settings


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key-with-enough-entropy",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=30,
    )


def test_password_hash_can_be_verified_without_storing_plaintext() -> None:
    password = "Strong-password-123!"
    password_hash = hash_password(password)

    assert password not in password_hash
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_token_contains_user_subject_and_can_be_decoded(
    auth_settings: Settings,
) -> None:
    token = create_access_token("user-123", auth_settings)

    assert decode_access_token(token, auth_settings) == "user-123"


def test_expired_access_token_is_rejected(auth_settings: Settings) -> None:
    token = create_access_token(
        "user-123",
        auth_settings,
        now=datetime(2020, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, auth_settings)


def test_refresh_token_is_random_and_only_hash_is_persisted() -> None:
    token = generate_refresh_token()

    assert len(token) >= 32
    assert hash_refresh_token(token) != token
    assert hash_refresh_token(token) == hash_refresh_token(token)
