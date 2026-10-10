import os
from dataclasses import dataclass
from logging import getLevelNamesMapping
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


@dataclass(frozen=True)
class Settings:
    app_name: str = "BITAmin Backend"
    log_level: str = "INFO"
    database_path: Path = DEFAULT_DATABASE_PATH

    @classmethod
    def from_environment(cls) -> "Settings":
        app_name = os.getenv("BACKEND_APP_NAME", cls.app_name)
        log_level = os.getenv("BACKEND_LOG_LEVEL", cls.log_level).upper()
        database_path = Path(os.getenv("BACKEND_DB_PATH", str(cls.database_path)))
        if log_level not in getLevelNamesMapping():
            raise ValueError(f"Invalid BACKEND_LOG_LEVEL: {log_level}")
        return cls(
            app_name=app_name,
            log_level=log_level,
            database_path=database_path,
        )
