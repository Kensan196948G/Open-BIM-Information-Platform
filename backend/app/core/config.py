import re

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_SECRET_KEYS = {
    "",
    "dev-secret-key-change-in-production",
    "change_me_in_production_use_openssl_rand_hex_32",
    "test-secret-key",
    "e2e-secret-key",
}

WEAK_DB_PASSWORDS = {"bim_password", "change_me_in_production", "postgres", ""}
WEAK_MINIO_CREDENTIALS = {"minioadmin", "minioadmin123", "change_me_in_production", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "Open BIM Information Platform"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://bim_user:bim_password@localhost:5432/bim_platform"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "bim-containers"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Rate limiting (in-process; single-worker deployments only)
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW_SECONDS: int = 60
    REGISTER_RATE_LIMIT: int = 3
    REGISTER_RATE_WINDOW_SECONDS: int = 3600
    # Redis-backed shared rate limiting (multi-worker safe). The in-process
    # limiter is used as a short fallback when Redis is unavailable.
    RATE_LIMIT_BACKEND: str = "redis"

    # bcrypt cost (12 is the OWASP-recommended default)
    BCRYPT_ROUNDS: int = 12

    # Self-registration (production should set false and use admin-invited users)
    ALLOW_SELF_REGISTRATION: bool = True

    # Malware scanning (ClamAV / clamd)
    AV_ENABLED: bool = False
    CLAMD_HOST: str = "clamav"
    CLAMD_PORT: int = 3310
    CLAMD_TIMEOUT_SECONDS: int = 30

    # OIDC (Entra ID / HENNGE federation)
    OIDC_ENABLED: bool = False
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""
    OIDC_SCOPES: str = "openid profile email"
    OIDC_JWKS_URI: str = ""
    OIDC_JIT_ACTIVE: bool = True
    # Comma-separated email domain allowlist for OIDC JIT provisioning.
    # Empty (default) = any IdP user may be provisioned; production should set it.
    OIDC_ALLOWED_DOMAINS: str = ""

    # SMTP (outbound email notifications). Disabled by default — CI and local
    # dev never require a reachable SMTP server (see app.services.mail).
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@example.com"
    SMTP_USE_TLS: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def oidc_allowed_domains_list(self) -> list[str]:
        return [
            d.strip().lower() for d in self.OIDC_ALLOWED_DOMAINS.split(",") if d.strip()
        ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Refuse to start in production with weak/default credentials."""
        if self.ENVIRONMENT.lower() != "production":
            return self

        problems: list[str] = []
        if self.DEBUG:
            problems.append("DEBUG must be False when ENVIRONMENT=production")
        if self.ALLOW_SELF_REGISTRATION:
            problems.append(
                "ALLOW_SELF_REGISTRATION must be false when ENVIRONMENT=production "
                "(users must be provisioned by administrators or OIDC)"
            )
        if self.BCRYPT_ROUNDS < 10 or self.BCRYPT_ROUNDS > 14:
            problems.append("BCRYPT_ROUNDS must be between 10 and 14")
        if self.RATE_LIMIT_BACKEND not in {"redis", "memory"}:
            problems.append("RATE_LIMIT_BACKEND must be 'redis' or 'memory'")
        if self.SECRET_KEY in WEAK_SECRET_KEYS or len(self.SECRET_KEY) < 32:
            problems.append(
                "SECRET_KEY is missing, weak, or shorter than 32 characters"
            )
        db_password_match = re.search(
            r"://[^:]+:(?P<password>[^@]+)@", self.DATABASE_URL
        )
        db_password = db_password_match.group("password") if db_password_match else ""
        if db_password in WEAK_DB_PASSWORDS or "change_me" in db_password:
            problems.append("DATABASE_URL contains a default/weak database password")
        if (
            self.MINIO_SECRET_KEY in WEAK_MINIO_CREDENTIALS
            or len(self.MINIO_SECRET_KEY) < 16
        ):
            problems.append(
                "MINIO_SECRET_KEY is missing, weak, or shorter than 16 characters"
            )
        if self.MINIO_ACCESS_KEY in WEAK_MINIO_CREDENTIALS:
            problems.append("MINIO_ACCESS_KEY uses a default/weak value")
        if "localhost" in self.CORS_ORIGINS or "127.0.0.1" in self.CORS_ORIGINS:
            problems.append("CORS_ORIGINS must not contain localhost in production")

        if problems:
            raise ValueError(
                "Refusing to start in production with insecure settings: "
                + "; ".join(problems)
            )
        return self


settings = Settings()
