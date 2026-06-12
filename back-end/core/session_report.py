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
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_metric_card(label: str, value: Any, helper: str, accent: str) -> Table:
    content = Paragraph(
        (
            f'<font size="7" color="#64748b">{label.upper()}</font><br/>'
            f'<font size="16" color="#111827"><b>{_format_value(value)}</b></font><br/>'
            f'<font size="8" color="#475569">{helper}</font>'
        ),
        ParagraphStyle(
            "MetricCard",
            parent=getSampleStyleSheet()["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#111827"),
            spaceAfter=0,
        ),
    )
    card = Table([[content]], colWidths=[44 * mm])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    accent_bar = Table([[""]], colWidths=[3 * mm], rowHeights=[20 * mm])
    accent_bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    wrapper = Table([[accent_bar, card]], colWidths=[3 * mm, 48 * mm])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrapper


def _draw_page_decorations(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#111827"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(14 * mm, height - 10.5 * mm, "VeloVaquejo Pro")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawRightString(
        width - 14 * mm,
        height - 10.5 * mm,
        f"Relatório automático • Página {canvas.getPageNumber()}",
    )
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.8)
    canvas.line(14 * mm, height - 14 * mm, width - 14 * mm, height - 14 * mm)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(14 * mm, 10 * mm, f"Gerado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}")
    canvas.drawRightString(width - 14 * mm, 10 * mm, "Varquejada System")
    canvas.restoreState()


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
    segments = report_data.get("segments") or []
    compact_samples = _compact_samples(list(samples))

    session_id = int(session.get("session_id") or 0)
    timestamp = now.strftime("%Y%m%d-%H%M%S-%f")
    output_path = output_dir / f"session-{session_id:04d}-{timestamp}.pdf"

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=getSampleStyleSheet()["Title"],
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=getSampleStyleSheet()["Normal"],
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=getSampleStyleSheet()["Heading2"],
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        spaceBefore=8,
        spaceAfter=6,
    )
    hero_title_style = ParagraphStyle(
        "HeroTitle",
        parent=getSampleStyleSheet()["Title"],
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        spaceAfter=4,
    )
    hero_text_style = ParagraphStyle(
        "HeroText",
        parent=getSampleStyleSheet()["Normal"],
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
    )
    segment_style = ParagraphStyle(
        "ReportSegment",
        parent=getSampleStyleSheet()["Heading3"],
        textColor=colors.HexColor("#334155"),
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12,
        spaceBefore=5,
        spaceAfter=4,
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
    hero_left = Paragraph(
        (
            "<font size='20' color='#111827'><b>VeloVaquejo Pro</b></font><br/>"
            "<font size='10' color='#475569'>Relatório automático da sessão de medição</font><br/><br/>"
            f"<font size='8.5' color='#64748b'>Gerado em {_format_value(report_data.get('generated_at'))}</font><br/>"
            f"<font size='8.5' color='#64748b'>Motivo: {_format_value(report_data.get('reason'))}</font>"
        ),
        hero_title_style,
    )
    hero_right = Table(
        [
            [
                Paragraph(
                    (
                        "<font size='7' color='#64748b'>STATUS</font><br/>"
                        "<font size='14' color='#166534'><b>FINALIZADA</b></font><br/>"
                        f"<font size='8' color='#475569'>Medições acumuladas: {len(segments) or 1}</font>"
                    ),
                    hero_text_style,
                )
            ]
        ],
        colWidths=[44 * mm],
    )
    hero_right.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    hero_table = Table([[hero_left, hero_right]], colWidths=[118 * mm, 52 * mm])
    hero_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(hero_table)
    story.append(Spacer(1, 8))

    metrics_cards = Table(
        [
            [
                _build_metric_card("Amostras", metrics.get("sample_count"), "Pontos utilizados na análise", "#3B82F6"),
                _build_metric_card("Velocidade máx.", f"{metrics.get('max_speed_kmh', 0.0):.2f} km/h", "Pico registrado na sessão", "#F59E0B"),
                _build_metric_card("Velocidade média", f"{metrics.get('avg_speed_kmh', 0.0):.2f} km/h", "Média de todo o trecho", "#22C55E"),
                _build_metric_card("Consistência", f"{metrics.get('consistency_pct', 0.0):.2f}%", "Estabilidade do ritmo", "#A855F7"),
            ]
        ],
        colWidths=[45.5 * mm, 45.5 * mm, 45.5 * mm, 45.5 * mm],
    )
    metrics_cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(metrics_cards)
    story.append(Spacer(1, 8))

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
                ("Medições acumuladas", len(segments) or 1),
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
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
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
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
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

    if segments:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Medições registradas", section_style))
        for index, segment in enumerate(segments, start=1):
            segment_session = segment.get("session") or {}
            segment_capture = segment.get("capture") or {}
            segment_metrics = segment.get("metrics") or {}
            segment_markers = segment.get("markers") or []
            segment_samples = _compact_samples(list(segment.get("samples") or []), limit=12)

            story.append(Paragraph(f"Medição {index}", segment_style))
            story.append(
                _build_kv_table(
                    [
                        ("Session ID", segment_session.get("session_id")),
                        ("Fonte", segment_session.get("source_type")),
                        ("Arquivo / câmera", segment_session.get("source_value")),
                        ("Início", segment_session.get("session_started_at")),
                        ("Encerramento", segment_session.get("session_finished_at") or segment.get("generated_at")),
                        ("Amostras", segment_metrics.get("sample_count")),
                        ("Velocidade máxima", f"{segment_metrics.get('max_speed_kmh', 0.0):.2f} km/h"),
                        ("Velocidade média", f"{segment_metrics.get('avg_speed_kmh', 0.0):.2f} km/h"),
                        ("Distância", f"{segment_metrics.get('distance_m', 0.0):.2f} m"),
                        ("FPS", segment_capture.get("fps")),
                    ]
                )
            )

            if segment_markers:
                segment_marker_rows = [
                    ["Marcador", "Tempo", "Cor"],
                    *[
                        [
                            str(marker.get("label", "Evento")),
                            _format_timecode(float(marker.get("position_ms", 0) or 0) / 1000.0),
                            str(marker.get("color", "#3B82F6")),
                        ]
                        for marker in segment_markers
                    ],
                ]
                segment_marker_table = Table(segment_marker_rows, colWidths=[72 * mm, 38 * mm, 60 * mm])
                segment_marker_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
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
                story.append(segment_marker_table)

            if segment_samples:
                segment_sample_rows = [
                    ["Tempo", "Velocidade", "Distância", "Confiança"],
                    *[
                        [
                            _format_timecode(float(sample.get("position_seconds", 0.0) or 0.0)),
                            f"{float(sample.get('speed_kmh', 0.0) or 0.0):.2f} km/h",
                            f"{float(sample.get('distance_m', 0.0) or 0.0):.2f} m",
                            f"{float(sample.get('confidence', 0.0) or 0.0):.3f}",
                        ]
                        for sample in segment_samples
                    ],
                ]
                segment_sample_table = Table(segment_sample_rows, colWidths=[36 * mm, 42 * mm, 42 * mm, 38 * mm])
                segment_sample_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
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
                story.append(segment_sample_table)

            story.append(Spacer(1, 6))

    doc.build(story, onFirstPage=_draw_page_decorations, onLaterPages=_draw_page_decorations)
    return output_path
