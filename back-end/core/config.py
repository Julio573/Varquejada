from dataclasses import dataclass, field
import os


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "null",
        ]
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins + ["null"] if "null" not in origins else origins


@dataclass(slots=True)
class Settings:
    app_name: str = "Varquejada System API"
    app_version: str = "0.1.0"
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS"))
    )


settings = Settings()
