"""
WoundWatch — per-photo Doctor Review Report (PDF)

Builds a one/two-page PDF for a single wound photo after a doctor has reviewed it:
patient info, the wound photo (+ heatmap if available), AI screening metrics,
and the doctor's assessment, findings, advice, medications and follow-up date.
"""
import io
import os
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

NAVY = colors.HexColor("#2F2B6E")
LAV = colors.HexColor("#7F79B6")
MUTED = colors.HexColor("#8C8AAE")
LINE = colors.HexColor("#E8E7F0")
SOFT = colors.HexColor("#F7F6FB")
TEXT = colors.HexColor("#333333")

RISK_COLOR = {"GREEN": colors.HexColor("#2BA84A"), "YELLOW": colors.HexColor("#E89B2C"), "RED": colors.HexColor("#D64545")}
RISK_BG = {"GREEN": colors.HexColor("#E8F8EC"), "YELLOW": colors.HexColor("#FFF5E5"), "RED": colors.HexColor("#FDEAEA")}
AI_LABEL = {"GREEN": "Low risk", "YELLOW": "Moderate risk", "RED": "High risk"}
DOCTOR_LABEL = {
    "GREEN": "Healing well - continue routine care",
    "YELLOW": "Needs monitoring - follow advice below",
    "RED": "Visit hospital - in-person check needed",
}

IST = timedelta(hours=5, minutes=30)


def _ist(dt):
    """DB stores naive UTC; show IST in the report."""
    if not dt:
        return "N/A"
    return (dt + IST).strftime("%d %b %Y, %I:%M %p IST")


def _txt(s, fallback="-"):
    s = (s or "").strip()
    if not s:
        return fallback
    return escape(s).replace("\n", "<br/>")


def _fit_image(path, max_w, max_h):
    """Load an image (fix phone rotation, shrink big photos) and return a reportlab Image."""
    from PIL import Image as PILImage, ImageOps
    with PILImage.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1200, 1200))
        w, h = im.size
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    scale = min(max_w / w, max_h / h)
    return Image(buf, width=w * scale, height=h * scale)


def _heatmap_path(upload_dir, filename):
    hp = os.path.join(upload_dir, f"heatmap_{filename}")
    if os.path.exists(hp):
        return hp
    try:
        from wound_analyzer import generate_heatmap
        if generate_heatmap(os.path.join(upload_dir, filename), hp) and os.path.exists(hp):
            return hp
    except Exception:
        pass
    return None


def _days_post_op(surgery_date, photo_time):
    try:
        sd = datetime.strptime(surgery_date, "%Y-%m-%d")
        return max(0, (photo_time - sd).days)
    except Exception:
        return None


def build_review_report(patient, photo, doctor, upload_dir="uploads") -> io.BytesIO:
    buf = io.BytesIO()
    report_id = f"WW-{photo.id:05d}-{(photo.reviewed_at or datetime.utcnow()).strftime('%Y%m%d')}"

    def _page(canvas, doc):
        canvas.saveState()
        # top band
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(20 * mm, A4[1] - 9 * mm, "WoundWatch")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 9 * mm, f"Report ID: {report_id}")
        # footer
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(A4[0] / 2, 10 * mm,
            "AI scores are a screening aid, not a diagnosis. The doctor's assessment above is the clinical opinion. "
            "In an emergency, go to the nearest hospital.")
        canvas.drawRightString(A4[0] - 20 * mm, 6 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            title=f"WoundWatch Review Report {report_id}", author=doctor.name if doctor else "WoundWatch")

    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontSize=20, textColor=NAVY, alignment=TA_LEFT, spaceAfter=2)
    sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=9.5, textColor=MUTED, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, textColor=NAVY, spaceBefore=9, spaceAfter=5)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, leading=14, textColor=TEXT)
    small = ParagraphStyle("sm", parent=body, fontSize=8.5, leading=11, textColor=MUTED)
    label = ParagraphStyle("l", parent=body, fontName="Helvetica-Bold", textColor=NAVY)
    cap = ParagraphStyle("c", parent=small, alignment=TA_CENTER)

    el = []
    el.append(Paragraph("Wound Review Report", title))
    el.append(Paragraph(f"Photo captured {_ist(photo.upload_time)} &nbsp;&middot;&nbsp; Reviewed {_ist(photo.reviewed_at)}", sub))
    el.append(HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=6))

    # ---- Patient ----
    el.append(Paragraph("Patient", h2))
    dpo = _days_post_op(patient.surgery_date or "", photo.upload_time) if photo.upload_time else None
    pinfo = [
        [Paragraph("Name", label), Paragraph(_txt(patient.name, "N/A"), body),
         Paragraph("Phone", label), Paragraph(_txt(patient.phone), body)],
        [Paragraph("Age / Gender", label), Paragraph(f"{patient.age or 'N/A'} / {_txt(patient.gender, 'N/A')}", body),
         Paragraph("Surgery", label), Paragraph(_txt(patient.surgery_type, "N/A"), body)],
        [Paragraph("Surgery date", label), Paragraph(_txt(patient.surgery_date, "N/A"), body),
         Paragraph("Post-op day", label), Paragraph(f"Day {dpo}" if dpo is not None else "N/A", body)],
    ]
    t = Table(pinfo, colWidths=[30 * mm, 55 * mm, 33 * mm, 52 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.white),
    ]))
    el.append(t)

    # ---- Doctor review ----
    da = photo.doctor_assessment or ""
    dc = RISK_COLOR.get(da, LAV)
    review = []
    review.append(Paragraph("Doctor's review", h2))
    badge = Table([[Paragraph(f"<font color='{dc.hexval().replace('0x', '#')}'><b>{escape(DOCTOR_LABEL.get(da, da or 'Reviewed'))}</b></font>", body)]],
                  colWidths=[170 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RISK_BG.get(da, SOFT)),
        ("BOX", (0, 0), (-1, -1), 1.2, dc),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    review.append(badge)
    review.append(Spacer(1, 8))
    rows = [
        [Paragraph("Findings", label), Paragraph(_txt(photo.doctor_findings or photo.doctor_notes), body)],
        [Paragraph("Advice / care", label), Paragraph(_txt(photo.doctor_advice), body)],
        [Paragraph("Medications", label), Paragraph(_txt(photo.doctor_medications, "No change"), body)],
        [Paragraph("Next follow-up", label), Paragraph(_txt(photo.followup_date, "As needed"), body)],
    ]
    rt = Table(rows, colWidths=[36 * mm, 134 * mm])
    rt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]))
    review.append(rt)
    # ---- Sign-off (part of the doctor's review block) ----
    review.append(Spacer(1, 6))
    dname = doctor.name if doctor else (photo.reviewed_by or "Doctor")
    dmeta = "  |  ".join(x for x in [escape(doctor.specialization or "") if doctor else "",
                                          escape(doctor.hospital or "") if doctor else ""] if x)
    sign = Table([
        [Paragraph(f"<b>Reviewed by:</b> {escape(dname)} ({escape(photo.reviewed_by or '')})", body), ""],
        [Paragraph(dmeta or "&nbsp;", small), Paragraph("Signature: _______________", body)],
        [Paragraph(f"Reviewed on {_ist(photo.reviewed_at)}", small), ""],
    ], colWidths=[100 * mm, 70 * mm])
    sign.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    review.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=4))
    review.append(sign)

    el.append(KeepTogether(review))

    # ---- Photo(s) ----
    el.append(Paragraph("Wound photo", h2))
    photo_path = os.path.join(upload_dir, photo.filename or "")
    imgs, caps = [], []
    if photo.filename and os.path.exists(photo_path):
        try:
            hp = _heatmap_path(upload_dir, photo.filename)
            box_w = 82 * mm if hp else 120 * mm
            imgs.append(_fit_image(photo_path, box_w, 50 * mm)); caps.append(Paragraph("Original photo", cap))
            if hp:
                imgs.append(_fit_image(hp, box_w, 50 * mm)); caps.append(Paragraph("AI heatmap (red = areas of concern)", cap))
        except Exception:
            imgs = []
    if imgs:
        pt = Table([imgs, caps], colWidths=[170 * mm / len(imgs)] * len(imgs))
        pt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        el.append(pt)
    else:
        el.append(Paragraph("Photo file not available.", small))

    # ---- AI screening ----
    lvl = photo.risk_level or "YELLOW"
    rc = RISK_COLOR.get(lvl, LAV)
    ai_block = [Paragraph("AI screening result", h2)]
    ai = [
        ["Risk level", "Risk score", "Redness", "Swelling", "Colour drift"],
        [AI_LABEL.get(lvl, lvl), f"{(photo.risk_score or 0) * 100:.0f}%",
         f"{photo.redness_index or 0:.0f}", f"{photo.swelling_score or 0:.0f}", f"{photo.color_deviation or 0:.0f}"],
    ]
    at = Table(ai, colWidths=[34 * mm] * 5)
    at.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TEXTCOLOR", (0, 1), (0, 1), rc), ("FONTNAME", (0, 1), (1, 1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
    ]))
    ai_block += [at, Spacer(1, 4),
                 Paragraph(f"<b>AI note:</b> {_txt(photo.recommendation)}", small),
                 Paragraph("Redness / swelling / colour drift are 0-100 indices from the image (higher = more concern).", small)]
    el.append(KeepTogether(ai_block))

    doc.build(el, onFirstPage=_page, onLaterPages=_page)
    buf.seek(0)
    return buf
