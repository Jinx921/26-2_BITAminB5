import os
from dataclasses import dataclass
from logging import getLevelNamesMapping
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
DEVELOPMENT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:3000",
)
DEVELOPMENT_QUESTION_RATE_LIMITS = {
    "citizen": 10,
    "admin": 30,
}
DEVELOPMENT_QUESTION_RATE_WINDOW_SECONDS = 60
DEFAULT_QUESTION_MAX_CONCURRENCY = 2


@dataclass(frozen=True)
class Settings:
    app_name: str = "BITAmin Backend"
    log_level: str = "INFO"
    database_path: Path = DEFAULT_DATABASE_PATH
    environment: str = "development"
    jwt_secret: str | None = None
    allowed_origins: tuple[str, ...] = DEVELOPMENT_ALLOWED_ORIGINS
    citizen_question_rate_limit: int | None = None
    admin_question_rate_limit: int | None = None
    question_rate_window_seconds: int | None = None
    question_max_concurrency: int = DEFAULT_QUESTION_MAX_CONCURRENCY

    @classmethod
    def from_environment(cls) -> "Settings":
        app_name = os.getenv("BACKEND_APP_NAME", cls.app_name)
        log_level = os.getenv("BACKEND_LOG_LEVEL", cls.log_level).upper()
        database_path = Path(os.getenv("BACKEND_DB_PATH", str(cls.database_path)))
        environment = os.getenv("BACKEND_ENVIRONMENT", cls.environment).lower()
        jwt_secret = os.getenv("BACKEND_JWT_SECRET")
        configured_origins = os.getenv("BACKEND_ALLOWED_ORIGINS")
        if configured_origins is None:
            allowed_origins = (
                DEVELOPMENT_ALLOWED_ORIGINS
                if environment == "development"
                else ()
            )
        else:
            allowed_origins = tuple(
                origin.strip()
                for origin in configured_origins.split(",")
                if origin.strip()
            )
        rate_limit_defaults = (
            DEVELOPMENT_QUESTION_RATE_LIMITS
            if environment == "development"
            else {}
        )
        citizen_question_rate_limit = cls._positive_integer(
            "BACKEND_QUESTION_RATE_LIMIT_CITIZEN",
            rate_limit_defaults.get("citizen"),
        )
        admin_question_rate_limit = cls._positive_integer(
            "BACKEND_QUESTION_RATE_LIMIT_ADMIN",
            rate_limit_defaults.get("admin"),
        )
        question_rate_window_seconds = cls._positive_integer(
            "BACKEND_QUESTION_RATE_WINDOW_SECONDS",
            (
                DEVELOPMENT_QUESTION_RATE_WINDOW_SECONDS
                if environment == "development"
                else None
            ),
        )
        question_max_concurrency = cls._positive_integer(
            "BACKEND_QUESTION_MAX_CONCURRENCY",
            DEFAULT_QUESTION_MAX_CONCURRENCY,
        )
        if question_max_concurrency is None:
            raise ValueError("BACKEND_QUESTION_MAX_CONCURRENCY must be configured")
        if log_level not in getLevelNamesMapping():
            raise ValueError(f"Invalid BACKEND_LOG_LEVEL: {log_level}")
        return cls(
            app_name=app_name,
            log_level=log_level,
            database_path=database_path,
            environment=environment,
            jwt_secret=jwt_secret,
            allowed_origins=allowed_origins,
            citizen_question_rate_limit=citizen_question_rate_limit,
            admin_question_rate_limit=admin_question_rate_limit,
            question_rate_window_seconds=question_rate_window_seconds,
            question_max_concurrency=question_max_concurrency,
        )

    @staticmethod
    def _positive_integer(name: str, default: int | None) -> int | None:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            parsed = int(value)
        except ValueError:
            raise ValueError(f"{name} must be a positive integer") from None
        if parsed <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return parsed

    def validate_allowed_origins(self) -> None:
        if self.environment in {"production", "prod"}:
            if not self.allowed_origins or "*" in self.allowed_origins:
                raise RuntimeError(
                    "BACKEND_ALLOWED_ORIGINS must contain explicit origins in production"
                )

    def validate_question_rate_limits(self) -> None:
        if self.environment != "development" and any(
            value is None
            for value in (
                self.citizen_question_rate_limit,
                self.admin_question_rate_limit,
                self.question_rate_window_seconds,
            )
        ):
            raise RuntimeError(
                "BACKEND_QUESTION_RATE_LIMIT_CITIZEN, "
                "BACKEND_QUESTION_RATE_LIMIT_ADMIN, and "
                "BACKEND_QUESTION_RATE_WINDOW_SECONDS must be configured "
                "outside development"
            )
