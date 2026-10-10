import os
from dataclasses import dataclass
from logging import getLevelNamesMapping


@dataclass(frozen=True)
class Settings:
    app_name: str = "BITAmin Backend"
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        app_name = os.getenv("BACKEND_APP_NAME", cls.app_name)
        log_level = os.getenv("BACKEND_LOG_LEVEL", cls.log_level).upper()
        if log_level not in getLevelNamesMapping():
            raise ValueError(f"Invalid BACKEND_LOG_LEVEL: {log_level}")
        return cls(app_name=app_name, log_level=log_level)
