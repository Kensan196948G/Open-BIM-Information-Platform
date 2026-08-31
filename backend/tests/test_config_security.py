"""Production startup guard tests.

Settings must refuse to start with weak/default credentials when
ENVIRONMENT=production, while remaining permissive for development/test.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _strong_production(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "x" * 64,
        "DATABASE_URL": (
            "postgresql+asyncpg://bim_user:Strong-Password-9f8a@db:5432/bim"
        ),
        "MINIO_ACCESS_KEY": "bim-storage-admin",
        "MINIO_SECRET_KEY": "y" * 24,
        "CORS_ORIGINS": "https://bim.example.com",
        "ALLOW_SELF_REGISTRATION": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_strong_production_config_accepted() -> None:
    settings = _strong_production()
    assert settings.ENVIRONMENT == "production"
    assert settings.DEBUG is False


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "dev-secret-key-change-in-production",
        "change_me_in_production_use_openssl_rand_hex_32",
        "short",
    ],
)
def test_weak_secret_rejected_in_production(secret: str) -> None:
    with pytest.raises(ValidationError, match="Refusing to start in production"):
        _strong_production(SECRET_KEY=secret)


def test_weak_database_password_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="default/weak database password"):
        _strong_production(
            DATABASE_URL="postgresql+asyncpg://bim_user:bim_password@db:5432/bim"
        )


@pytest.mark.parametrize(
    "secret",
    ["", "minioadmin123", "change_me_in_production", "short"],
)
def test_weak_minio_secret_rejected_in_production(secret: str) -> None:
    with pytest.raises(ValidationError, match="MINIO_SECRET_KEY"):
        _strong_production(MINIO_SECRET_KEY=secret)


def test_weak_minio_access_key_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="MINIO_ACCESS_KEY"):
        _strong_production(MINIO_ACCESS_KEY="minioadmin")


def test_debug_true_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be False"):
        _strong_production(DEBUG=True)


def test_localhost_cors_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        _strong_production(CORS_ORIGINS="http://localhost:5173")


def test_self_registration_rejected_in_production() -> None:
    """Open self-registration must be explicitly disabled for production."""
    with pytest.raises(ValidationError, match="ALLOW_SELF_REGISTRATION"):
        _strong_production(ALLOW_SELF_REGISTRATION=True)


def test_invalid_bcrypt_rounds_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="BCRYPT_ROUNDS"):
        _strong_production(BCRYPT_ROUNDS=8)


def test_invalid_rate_limit_backend_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="RATE_LIMIT_BACKEND"):
        _strong_production(RATE_LIMIT_BACKEND="file")


def test_download_temp_global_limit_must_cover_request_limit() -> None:
    with pytest.raises(ValidationError, match="DOWNLOAD_TEMP_GLOBAL_LIMIT_BYTES"):
        Settings(
            _env_file=None,
            DOWNLOAD_TEMP_REQUEST_LIMIT_BYTES=20,
            DOWNLOAD_TEMP_GLOBAL_LIMIT_BYTES=10,
        )


def test_download_temp_request_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="DOWNLOAD_TEMP_REQUEST_LIMIT_BYTES"):
        Settings(_env_file=None, DOWNLOAD_TEMP_REQUEST_LIMIT_BYTES=0)


def test_self_registration_optional_in_development() -> None:
    settings = Settings(_env_file=None)
    assert settings.ALLOW_SELF_REGISTRATION is True


def test_development_defaults_remain_permissive(monkeypatch) -> None:
    for key in (
        "ENVIRONMENT",
        "SECRET_KEY",
        "DEBUG",
        "DATABASE_URL",
        "MINIO_SECRET_KEY",
        "MINIO_ACCESS_KEY",
        "CORS_ORIGINS",
        "AV_ENABLED",
        "OIDC_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.ENVIRONMENT == "development"
    assert settings.SECRET_KEY == "dev-secret-key-change-in-production"
