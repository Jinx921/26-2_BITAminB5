import os
from dataclasses import dataclass
from logging import getLevelNamesMapping
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
DEVELOPMENT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:3000",
)


@dataclass(frozen=True)
class Settings:
    app_name: str = "BITAmin Backend"
    log_level: str = "INFO"
    database_path: Path = DEFAULT_DATABASE_PATH
    environment: str = "development"
    jwt_secret: str | None = None
    allowed_origins: tuple[str, ...] = DEVELOPMENT_ALLOWED_ORIGINS

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
        if log_level not in getLevelNamesMapping():
            raise ValueError(f"Invalid BACKEND_LOG_LEVEL: {log_level}")
        return cls(
            app_name=app_name,
            log_level=log_level,
            database_path=database_path,
            environment=environment,
            jwt_secret=jwt_secret,
            allowed_origins=allowed_origins,
        )

    def validate_allowed_origins(self) -> None:
        if self.environment in {"production", "prod"}:
            if not self.allowed_origins or "*" in self.allowed_origins:
                raise RuntimeError(
                    "BACKEND_ALLOWED_ORIGINS must contain explicit origins in production"
                )
