from pathlib import Path
from mimetypes import guess_type

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from api.dependencies import get_session_streamer
from core.frame_streamer import SessionFrameStreamer

router = APIRouter()


@router.get("/file")
async def media_file(path: str = Query(..., description="Caminho absoluto do arquivo de mídia")):
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {file_path}")

    media_type, _ = guess_type(file_path.name)
    return FileResponse(file_path, media_type=media_type or "application/octet-stream", filename=file_path.name)


@router.get("/video-feed")
async def video_feed(
    request: Request,
    streamer: SessionFrameStreamer = Depends(get_session_streamer),
):
    boundary = "frame"

    async def stream():
        last_version = -1
        while True:
            if await request.is_disconnected():
                break

            frame_bytes, version = streamer.get_latest_frame()
            if frame_bytes is None:
                await asyncio.sleep(0.05)
                continue

            if version == last_version:
                await asyncio.sleep(0.03)
                continue

            last_version = version
            yield (
                f"--{boundary}\r\n"
                "Content-Type: image/jpeg\r\n"
                f"Content-Length: {len(frame_bytes)}\r\n\r\n"
            ).encode("ascii") + frame_bytes + b"\r\n"
            await asyncio.sleep(0.001)

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    return StreamingResponse(stream(), media_type=f"multipart/x-mixed-replace; boundary={boundary}", headers=headers)


@router.get("/snapshot")
async def media_snapshot(
    streamer: SessionFrameStreamer = Depends(get_session_streamer),
):
    frame_bytes, _ = streamer.get_latest_frame()
    if frame_bytes is None:
        raise HTTPException(status_code=404, detail="Nenhuma imagem disponível para captura.")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Content-Disposition": 'attachment; filename="screenshot.jpg"',
    }
    return Response(content=frame_bytes, media_type="image/jpeg", headers=headers)
