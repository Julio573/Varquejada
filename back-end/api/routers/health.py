from datetime import datetime, timezone

from fastapi import APIRouter

from core.config import settings

router = APIRouter(tags=["health"])


@router.api_route("/health", methods=["GET", "HEAD"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
