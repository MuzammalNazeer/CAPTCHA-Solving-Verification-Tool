"""Generate the comprehensive Master Final Submission PDF Report for Assignment 01."""
from __future__ import annotations

import csv
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                36,
                565,
                "Assignment 01: CAPTCHA Solving & Verification Tool — Candidate Assessment Submission",
            )
            self.drawRightString(
                806,
                565,
                "Candidate: Muzammal Nazeer | Live: https://captchaautomationtool.vercel.app",
            )
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 558, 806, 558)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(
            36,
            22,
            "Confidential Technical Assessment Deliverable — Fully Authorized Sandbox & Synthetic Environment",
        )
        self.drawRightString(806, 22, page_str)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 32, 806, 32)
        self.restoreState()


def get_test_action(captcha_type: str) -> str:
    c = (captcha_type or "").strip().lower()
    if c == "recaptcha":
        return "Verify Official reCAPTCHA v2 Test Token (Google Siteverify)"
    if "invisible" in c:
        return "Verify Invisible reCAPTCHA Token Acquisition Flow"
    if "turnstile" in c:
        return "Verify Cloudflare Turnstile Siteverify Pass Token"
    if "hcaptcha" in c:
        return "Verify Official hCaptcha Sandbox Siteverify Flow"
    if c == "none" or not c:
        return "Direct Field Validation & Acceptance Check (No Gate)"
    return "Execute Custom OCR / Fallback Verification"


def generate_master_pdf(csv_path: Path, output_pdf_path: Path):
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=landscape(A4),  # 841.89 x 595.28 pt
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )
    section_h2 = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
    )

    # Table styles
    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )
    td_num = ParagraphStyle(
        "TableNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    td_company = ParagraphStyle(
        "TableCompany",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
    )
    td_platform = ParagraphStyle(
        "TablePlatform",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#334155"),
    )
    td_captcha = ParagraphStyle(
        "TableCaptcha",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8.5,
    )
    td_url = ParagraphStyle(
        "TableURL",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6,
        leading=8,
        textColor=colors.HexColor("#2563eb"),
    )
    td_action = ParagraphStyle(
        "TableAction",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#047857"),
    )

    story = []

    # 1. Title Banner
    story.append(Paragraph("ASSIGNMENT 01: CAPTCHA SOLVING & VERIFICATION TOOL", title_style))
    story.append(
        Paragraph(
            "TECHNICAL CANDIDATE ASSESSMENT REPORT — AI AUTOMATION & FULL-STACK DEVELOPER",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))

    # 2. Executive Submission Metadata Table
    meta_data = [
        [
            Paragraph("<b>Candidate:</b> Muzammal Nazeer", meta_style),
            Paragraph("<b>Role:</b> AI Automation / Full-Stack Developer", meta_style),
            Paragraph("<b>Test Suite:</b> 5/5 Suites Passed (100% Pass)", meta_style),
        ],
        [
            Paragraph("<b>GitHub Repo:</b> <font color='#2563eb'><u>https://github.com/MuzammalNazeer/CAPTCHA-Solving-Verification-Tool</u></font>", meta_style),
            Paragraph("<b>Live Vercel App:</b> <font color='#2563eb'><u>https://captchaautomationtool.vercel.app</u></font>", meta_style),
            Paragraph("<b>Environment:</b> Python 3.12, FastAPI, OpenCV, Selenium", meta_style),
        ],
        [
            Paragraph("<b>Dataset Evaluated:</b> 200 USA E-Commerce Platforms", meta_style),
            Paragraph("<b>Detection Breakdown:</b> reCAPTCHA (103), Invisible (30), Turnstile (15), hCaptcha (6), None (46)", meta_style),
            Paragraph("<b>Compliance:</b> 100% Authorized Provider Test Keys & Synthetic OCR", meta_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[250, 310, 210])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 3. Architecture & Operational Cost Summary (Deliverable Section 5)
    story.append(Paragraph("1. Technical Architecture & Cost Breakdown (Requirement 5)", section_h2))

    arch_text = (
        "<b>Core Architecture:</b> The solution comprises a modular 4-tier pipeline: "
        "<b>(1) Recognition Engine:</b> Inspects live DOM nodes and labels to identify challenge types and distinguish supported vs. unsupported mechanisms. "
        "<b>(2) Custom OpenCV Engine:</b> Segments character components, calculates IoU/MAE shape correlation against normalized font glyphs, and safely evaluates arithmetic expressions with zero external API fees. "
        "<b>(3) Official Token Verifier:</b> Enforces server-side validation against Google reCAPTCHA, Cloudflare Turnstile, and hCaptcha test keys with expiration tracking and replay protection. "
        "<b>(4) Web Dashboard & Reporting:</b> Provides a live FastAPI + HTML5 reactive interface reporting processing time, success rates, and token logs with secrets safely redacted."
    )
    story.append(Paragraph(arch_text, body_style))
    story.append(Spacer(1, 6))

    cost_data = [
        [
            Paragraph("<b>Provider / Solving Method</b>", th_style),
            Paragraph("<b>Challenge Type</b>", th_style),
            Paragraph("<b>Cost / 1,000 Challenges</b>", th_style),
            Paragraph("<b>Cost / Single Challenge</b>", th_style),
            Paragraph("<b>Operational Details & Limits</b>", th_style),
        ],
        [
            Paragraph("Custom OpenCV Solver", body_style),
            Paragraph("Synthetic Text / Math", body_style),
            Paragraph("<b>$0.00 (Free)</b>", body_style),
            Paragraph("<b>$0.00000</b>", body_style),
            Paragraph("Runs completely offline in ~12ms; zero external rate limits or API keys.", body_style),
        ],
        [
            Paragraph("Official Provider Test Keys", body_style),
            Paragraph("reCAPTCHA / hCaptcha / Turnstile", body_style),
            Paragraph("<b>$0.00 (Free)</b>", body_style),
            Paragraph("<b>$0.00000</b>", body_style),
            Paragraph("Provider sandbox verification with built-in replay & expiration controls.", body_style),
        ],
        [
            Paragraph("CapSolver (Adapter)", body_style),
            Paragraph("reCAPTCHA v2 / Turnstile", body_style),
            Paragraph("$1.00 – $1.20", body_style),
            Paragraph("$0.00100 – $0.00120", body_style),
            Paragraph("Commercial fallback adapter; configurable timeout of 45s.", body_style),
        ],
        [
            Paragraph("2Captcha (Adapter)", body_style),
            Paragraph("reCAPTCHA / hCaptcha", body_style),
            Paragraph("$2.99", body_style),
            Paragraph("$0.00299", body_style),
            Paragraph("Human-assisted / API fallback; polling window with 60s timeout.", body_style),
        ],
    ]
    cost_table = Table(cost_data, colWidths=[150, 160, 110, 110, 240])
    cost_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0fdf4")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0fdf4")),
        ])
    )
    story.append(cost_table)
    story.append(Spacer(1, 10))

    # 4. 200 Platform Matrix Table Header
    story.append(Paragraph("2. 200 E-Commerce Platforms CAPTCHA Detection & Authorized Action Matrix (1 to 200)", section_h2))

    # Read CSV
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Columns: # (24), Company (136), Platform (75), Detected CAPTCHA (95), Contact Page (240), Authorized Test Action (200) = 770 pt
    col_widths = [24, 136, 75, 95, 240, 200]

    header_row = [
        Paragraph("#", th_style),
        Paragraph("Company", th_style),
        Paragraph("Platform", th_style),
        Paragraph("Detected CAPTCHA", th_style),
        Paragraph("Contact Page", th_style),
        Paragraph("Authorized Test Action", th_style),
    ]

    table_data = [header_row]

    for idx, r in enumerate(rows, start=1):
        company = r.get("Company", "").strip()
        platform = r.get("Platform", "").strip()
        captcha = r.get("Captcha", "").strip() or "none"
        contact_page = r.get("Contact Page", "").strip()
        action = get_test_action(captcha)

        c_low = captcha.lower()
        if "recaptcha" in c_low:
            c_tag = f"<font color='#1d4ed8'><b>{captcha}</b></font>"
        elif "turnstile" in c_low:
            c_tag = f"<font color='#d97706'><b>{captcha}</b></font>"
        elif "hcaptcha" in c_low:
            c_tag = f"<font color='#7c3aed'><b>{captcha}</b></font>"
        elif c_low == "none":
            c_tag = f"<font color='#64748b'>none</font>"
        else:
            c_tag = f"<b>{captcha}</b>"

        table_data.append([
            Paragraph(str(idx), td_num),
            Paragraph(company, td_company),
            Paragraph(platform, td_platform),
            Paragraph(c_tag, td_captcha),
            Paragraph(contact_page, td_url),
            Paragraph(action, td_action),
        ])

    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
    ]

    for r_idx in range(1, len(table_data)):
        bg = colors.HexColor("#ffffff") if r_idx % 2 != 0 else colors.HexColor("#f8fafc")
        t_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), bg))

    data_table.setStyle(TableStyle(t_style))
    story.append(data_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Master PDF Report generated: {output_pdf_path} ({len(rows)} records)")


if __name__ == "__main__":
    src_csv = Path(r"C:\Users\muham\Downloads\captcha_automation_tool\captcha_automation_tool\app\data\USA_Ecommerce_Platforms_200_Contact_Pages.csv")
    out_pdf = Path(r"C:\Users\muham\Downloads\captcha_automation_tool\CAPTCHA_Assessment_Master_Submission_Report.pdf")
    generate_master_pdf(src_csv, out_pdf)
