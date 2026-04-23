"""
Generazione del report di audit finale in formato PDF.
Usa reportlab (puro Python, nessuna dipendenza esterna al sistema).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from .llm_verifier import VerificationResult


STATUS_COLORS = {
    "conforme": colors.HexColor("#1f7a1f"),
    "non_conforme": colors.HexColor("#b22222"),
    "parziale": colors.HexColor("#c78a00"),
    "non_verificabile": colors.HexColor("#666666"),
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(
        ParagraphStyle(
            name="H1Custom",
            fontName="Helvetica-Bold",
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor("#222222"),
        )
    )
    ss.add(
        ParagraphStyle(
            name="H2Custom",
            fontName="Helvetica-Bold",
            fontSize=14,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#333333"),
        )
    )
    ss.add(
        ParagraphStyle(
            name="H3Custom",
            fontName="Helvetica-Bold",
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#444444"),
        )
    )
    ss.add(
        ParagraphStyle(
            name="BodyCustom",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            spaceAfter=6,
        )
    )
    ss.add(
        ParagraphStyle(
            name="SmallCustom",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#555555"),
        )
    )
    return ss


def _status_badge(status: str) -> Paragraph:
    color = STATUS_COLORS.get(status, colors.black)
    label = status.replace("_", " ").upper()
    return Paragraph(
        f'<font color="{color.hexval()}"><b>{label}</b></font>',
        getSampleStyleSheet()["Normal"],
    )


def _executive_summary_table(results: List[VerificationResult], styles) -> Table:
    data = [["ID", "Controllo", "Esito", "Check point NC"]]
    for r in results:
        nc = sum(1 for cp in r.check_points if cp.status == "non_conforme")
        total = len(r.check_points)
        data.append(
            [
                r.control_id,
                Paragraph(r.control_title, styles["BodyCustom"]),
                _status_badge(r.overall_status),
                f"{nc}/{total}",
            ]
        )
    tbl = Table(data, colWidths=[1.5 * cm, 8.5 * cm, 3.5 * cm, 3 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (3, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def _check_points_table(result: VerificationResult, styles) -> Table:
    data = [["#", "Check Point", "Esito", "Evidenza / Issue"]]
    for i, cp in enumerate(result.check_points, start=1):
        issue_text = cp.evidence
        if cp.issue:
            issue_text += f"<br/><i>Issue:</i> {cp.issue}"
        data.append(
            [
                str(i),
                Paragraph(cp.check_point, styles["BodyCustom"]),
                _status_badge(cp.status),
                Paragraph(issue_text, styles["SmallCustom"]),
            ]
        )
    tbl = Table(data, colWidths=[0.8 * cm, 6.5 * cm, 3 * cm, 6.2 * cm], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tbl


def generate_pdf_report(
    results: List[VerificationResult],
    output_path: str | Path,
    title: str = "Internal Audit Report — Procure-to-Pay",
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = _styles()
    story = []

    # --- Header ---
    story.append(Paragraph(title, styles["H1Custom"]))
    story.append(
        Paragraph(
            f"Data esecuzione: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["SmallCustom"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # --- Executive summary ---
    story.append(Paragraph("Executive Summary", styles["H2Custom"]))

    total = len(results)
    conformi = sum(1 for r in results if r.overall_status == "conforme")
    non_conformi = sum(1 for r in results if r.overall_status == "non_conforme")
    parziali = total - conformi - non_conformi

    story.append(
        Paragraph(
            f"Sono stati eseguiti <b>{total}</b> controlli: "
            f"<font color='#1f7a1f'><b>{conformi}</b> conformi</font>, "
            f"<font color='#b22222'><b>{non_conformi}</b> non conformi</font>, "
            f"<font color='#c78a00'><b>{parziali}</b> parziali</font>.",
            styles["BodyCustom"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(_executive_summary_table(results, styles))

    # --- Dettaglio per ogni controllo ---
    for r in results:
        story.append(PageBreak())
        story.append(
            Paragraph(f"Controllo {r.control_id} — {r.control_title}", styles["H2Custom"])
        )
        story.append(
            Paragraph(
                f"<b>Esito complessivo:</b> "
                f"<font color='{STATUS_COLORS.get(r.overall_status, colors.black).hexval()}'>"
                f"<b>{r.overall_status.replace('_', ' ').upper()}</b></font>",
                styles["BodyCustom"],
            )
        )
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("Sintesi", styles["H3Custom"]))
        story.append(Paragraph(r.summary or "—", styles["BodyCustom"]))

        story.append(Paragraph("Dettaglio Check Points", styles["H3Custom"]))
        story.append(_check_points_table(r, styles))

        if r.mitigation_plan:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Piano di Mitigazione", styles["H3Custom"]))
            for i, m in enumerate(r.mitigation_plan, start=1):
                story.append(Paragraph(f"<b>{i}.</b> {m}", styles["BodyCustom"]))

    doc.build(story)
    return output_path
