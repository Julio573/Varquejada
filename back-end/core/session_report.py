from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _format_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_value(item) for item in value)
    return str(value)


def _format_timecode(seconds: float | None) -> str:
    if seconds is None:
        return "—"

    total_ms = max(0, int(seconds * 1000))
    minutes = total_ms // 60000
    remaining_seconds = (total_ms // 1000) % 60
    millis = (total_ms % 1000) // 10
    return f"{minutes:02d}:{remaining_seconds:02d}.{millis:02d}"


def _build_kv_table(rows: list[tuple[str, Any]]) -> Table:
    data = [[label, _format_value(value)] for label, value in rows]
    table = Table(data, colWidths=[58 * mm, 112 * mm], repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#334155")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#0f172a"), colors.HexColor("#111827")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _compact_samples(samples: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    if len(samples) <= limit:
        return samples

    step = max(1, len(samples) // limit)
    compacted = samples[::step]
    if compacted[-1] != samples[-1]:
        compacted.append(samples[-1])
    return compacted[:limit]


def build_session_report(report_data: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    session = report_data.get("session") or {}
    capture = report_data.get("capture") or {}
    metrics = report_data.get("metrics") or {}
    markers = report_data.get("markers") or []
    samples = report_data.get("samples") or []
    compact_samples = _compact_samples(list(samples))

    session_id = int(session.get("session_id") or 0)
    timestamp = now.strftime("%Y%m%d-%H%M%S-%f")
    output_path = output_dir / f"session-{session_id:04d}-{timestamp}.pdf"

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=getSampleStyleSheet()["Title"],
        textColor=colors.HexColor("#f8fafc"),
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=getSampleStyleSheet()["Normal"],
        textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=getSampleStyleSheet()["Heading2"],
        textColor=colors.HexColor("#e2e8f0"),
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        spaceBefore=8,
        spaceAfter=6,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="VeloVaquejo Pro - Relatório de Sessão",
        author="Varquejada System",
    )

    story: list[Any] = []
    story.append(Paragraph("VeloVaquejo Pro", title_style))
    story.append(Paragraph("Relatório automático da sessão de medição", subtitle_style))
    story.append(
        Paragraph(
            f"Gerado em {_format_value(report_data.get('generated_at'))} "
            f" | Motivo: {_format_value(report_data.get('reason'))}",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 4))
    story.append(Paragraph("Informações da sessão", section_style))
    story.append(
        _build_kv_table(
            [
                ("Session ID", session.get("session_id")),
                ("Fonte", session.get("source_type")),
                ("Arquivo / câmera", session.get("source_value")),
                ("Início", session.get("session_started_at")),
                ("Encerramento", session.get("session_finished_at") or report_data.get("generated_at")),
                ("Status", "Finalizada"),
                ("Último relatório", session.get("last_report_path")),
            ]
        )
    )

    story.append(Spacer(1, 8))
    story.append(Paragraph("Capture / origem", section_style))
    story.append(
        _build_kv_table(
            [
                ("Resolução", f"{capture.get('width') or '—'} × {capture.get('height') or '—'}"),
                ("FPS", capture.get("fps")),
                ("Duração", _format_timecode(capture.get("duration_seconds"))),
                ("Posição final", _format_timecode(capture.get("position_seconds"))),
                ("Frames", capture.get("frame_count")),
            ]
        )
    )

    story.append(Spacer(1, 8))
    story.append(Paragraph("Métricas principais", section_style))
    story.append(
        _build_kv_table(
            [
                ("Amostras", metrics.get("sample_count")),
                ("Velocidade máxima", f"{metrics.get('max_speed_kmh', 0.0):.2f} km/h"),
                ("Velocidade média", f"{metrics.get('avg_speed_kmh', 0.0):.2f} km/h"),
                ("Velocidade mínima", f"{metrics.get('min_speed_kmh', 0.0):.2f} km/h"),
                ("Tendência", f"{metrics.get('trend_kmh', 0.0):.2f} km/h"),
                ("Aceleração pico", f"{metrics.get('peak_acceleration_kmh_s', 0.0):.2f} km/h/s"),
                ("Tempo acima de 40 km/h", f"{metrics.get('time_above_40_s', 0.0):.2f} s"),
                ("Consistência", f"{metrics.get('consistency_pct', 0.0):.2f}%"),
                ("Distância estimada", f"{metrics.get('distance_m', 0.0):.2f} m"),
                ("Confiança média", f"{metrics.get('avg_confidence', 0.0):.3f}"),
                ("Duração amostrada", f"{metrics.get('duration_seconds') or 0.0:.2f} s"),
            ]
        )
    )

    story.append(Spacer(1, 8))
    story.append(Paragraph("Marcadores", section_style))
    if markers:
        marker_rows = [
            ["Marcador", "Tempo", "Cor"],
            *[
                [
                    str(marker.get("label", "Evento")),
                    _format_timecode(float(marker.get("position_ms", 0) or 0) / 1000.0),
                    str(marker.get("color", "#3B82F6")),
                ]
                for marker in markers
            ],
        ]
        marker_table = Table(marker_rows, colWidths=[72 * mm, 38 * mm, 60 * mm])
        marker_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#334155")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0f172a"), colors.HexColor("#111827")]),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEADING", (0, 0), (-1, -1), 11),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(marker_table)
    else:
        story.append(Paragraph("Nenhum marcador registrado nesta sessão.", subtitle_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Amostras de velocidade", section_style))
    if compact_samples:
        sample_rows = [
            ["Tempo", "Velocidade", "Distância", "Confiança"],
            *[
                [
                    _format_timecode(float(sample.get("position_seconds", 0.0) or 0.0)),
                    f"{float(sample.get('speed_kmh', 0.0) or 0.0):.2f} km/h",
                    f"{float(sample.get('distance_m', 0.0) or 0.0):.2f} m",
                    f"{float(sample.get('confidence', 0.0) or 0.0):.3f}",
                ]
                for sample in compact_samples
            ],
        ]
        sample_table = Table(sample_rows, colWidths=[36 * mm, 42 * mm, 42 * mm, 38 * mm])
        sample_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#334155")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0f172a"), colors.HexColor("#111827")]),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(sample_table)
    else:
        story.append(Paragraph("Sem amostras suficientes para o relatório.", subtitle_style))

    doc.build(story)
    return output_path
