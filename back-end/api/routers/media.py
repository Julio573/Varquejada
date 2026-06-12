from pathlib import Path
from mimetypes import guess_type

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/file")
async def media_file(path: str = Query(..., description="Caminho absoluto do arquivo de mídia")):
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {file_path}")

    media_type, _ = guess_type(file_path.name)
    return FileResponse(file_path, media_type=media_type or "application/octet-stream", filename=file_path.name)
