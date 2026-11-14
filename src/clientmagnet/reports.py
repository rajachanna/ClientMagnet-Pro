"""Generate a readable, evidence-linked PDF audit report with ReportLab."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def pdf_bytes(report: dict, brand: str = "NextGen Tech Solutions") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
                            topMargin=18 * mm, bottomMargin=19 * mm)
    title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=21, leading=25,
                           textColor=colors.HexColor("#0D2640"), spaceAfter=12)
    normal = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=14,
                            textColor=colors.HexColor("#28394A"), spaceAfter=5)
    small = ParagraphStyle("small", parent=normal, fontSize=8, leading=12)
    heading = ParagraphStyle("heading", parent=normal, fontName="Helvetica-Bold", fontSize=12,
                             leading=17, textColor=colors.HexColor("#0C625A"), spaceBefore=12)
    story = [Paragraph("Website Diagnostic Report", title),
             Paragraph(escape(brand), normal),
             Paragraph("<b>Website:</b> " + escape(report["url"]), normal),
             Paragraph("<b>Source:</b> " + escape(report["source"]) + " · " + escape(report["created_utc"][:10]), normal),
             Spacer(1, 9)]
    s = report["scores"]
    metrics = [["Overall", "SEO", "Accessibility", "Conversion"],
               [str(s["overall"]), str(s["seo"]), str(s["accessibility"]), str(s["conversion"])]]
    t = Table(metrics, colWidths=[44 * mm, 42 * mm, 43 * mm, 42 * mm], rowHeights=[20, 32])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF7F5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#37665E")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#153A37")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 17),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, -1), (-1, -1), .5, colors.HexColor("#BDD8D0")),
    ]))
    story += [t, Paragraph("Priority fixes", heading)]
    issues = report["priority_recommendations"]
    if not issues:
        story.append(Paragraph("No issues detected by the included HTML checks.", normal))
    for i, issue in enumerate(issues, 1):
        story.append(KeepTogether([
            Paragraph(f"<b>{i}. {escape(issue['title'])}</b>", normal),
            Paragraph(escape(issue["recommendation"]), normal),
            Paragraph("Evidence: " + escape(issue["evidence"]), small),
            Spacer(1, 6),
        ]))
    story.append(Paragraph("Diagnostic checks", heading))
    for check in report["checks"]:
        story.append(Paragraph(
            "<b>" + escape(check["status"].upper()) + "</b> · " + escape(check["label"]) +
            " — " + escape(check["evidence"]), small,
        ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("What this report does not measure", heading))
    story.append(Paragraph(escape(report["limitations"]), small))
    story.append(Paragraph("No guarantee of rankings, website speed, conversion uplift, or business revenue.", small))
    doc.build(story)
    return buf.getvalue()
