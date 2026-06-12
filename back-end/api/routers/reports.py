from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.dependencies import get_session_manager
from api.schemas import ReportItem
from core.session_manager import SessionManager

router = APIRouter()
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


@router.get("", response_model=list[ReportItem])
async def list_reports() -> list[ReportItem]:
    if not REPORTS_DIR.exists():
        return []

    reports: list[ReportItem] = []
    for report_path in sorted(REPORTS_DIR.glob("*.pdf"), key=lambda item: item.stat().st_mtime, reverse=True):
        stat = report_path.stat()
        reports.append(
            ReportItem(
                filename=report_path.name,
                path=str(report_path.resolve()),
                size_bytes=int(stat.st_size),
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return reports


@router.get("/latest")
async def get_latest_report(manager: SessionManager = Depends(get_session_manager)) -> FileResponse:
    if not manager.last_report_path:
        raise HTTPException(status_code=404, detail="Nenhum relatório foi gerado ainda.")

    report_path = Path(manager.last_report_path).expanduser().resolve()
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="O último relatório não foi encontrado.")

    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=report_path.name,
    )
