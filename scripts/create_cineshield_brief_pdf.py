from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "cineshield-brief-for-maam.pdf"
TMP = ROOT / "tmp" / "pdfs"

SCREENSHOTS = [
    Path("d:/C_drive_merge/OneDrive/Pictures/Screenshots/Screenshot 2026-08-26 074249.png"),
    Path("d:/C_drive_merge/OneDrive/Pictures/Screenshots/Screenshot 2026-08-26 074336.png"),
    Path("d:/C_drive_merge/OneDrive/Pictures/Screenshots/Screenshot 2026-08-26 074425.png"),
]

W, H = landscape(A4)
BG = colors.HexColor("#090A0A")
SURFACE = colors.HexColor("#111514")
SURFACE_2 = colors.HexColor("#18201D")
TEXT = colors.HexColor("#F4ECDD")
MUTED = colors.HexColor("#C0B6A8")
DIM = colors.HexColor("#7E776E")
GOLD = colors.HexColor("#E5AD49")
TEAL = colors.HexColor("#42D3C8")
JADE = colors.HexColor("#58BF83")
CORAL = colors.HexColor("#EF7564")
LINE = colors.Color(0.91, 0.89, 0.84, alpha=0.16)


STYLES = {
    "eyebrow": ParagraphStyle(
        "eyebrow",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=GOLD,
        uppercase=True,
        alignment=TA_LEFT,
    ),
    "title": ParagraphStyle(
        "title",
        fontName="Helvetica-Bold",
        fontSize=35,
        leading=38,
        textColor=TEXT,
        alignment=TA_LEFT,
    ),
    "page_title": ParagraphStyle(
        "page_title",
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=31,
        textColor=TEXT,
        alignment=TA_LEFT,
    ),
    "subhead": ParagraphStyle(
        "subhead",
        fontName="Helvetica",
        fontSize=16,
        leading=21,
        textColor=MUTED,
        alignment=TA_LEFT,
    ),
    "body": ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=12.2,
        leading=17,
        textColor=MUTED,
        alignment=TA_LEFT,
    ),
    "body_bold": ParagraphStyle(
        "body_bold",
        fontName="Helvetica-Bold",
        fontSize=12.2,
        leading=17,
        textColor=TEXT,
        alignment=TA_LEFT,
    ),
    "small": ParagraphStyle(
        "small",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=DIM,
        alignment=TA_LEFT,
    ),
    "center": ParagraphStyle(
        "center",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=TEXT,
        alignment=TA_CENTER,
    ),
}


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), STYLES[style])


def draw_para(c: canvas.Canvas, text: str, x: float, top: float, width: float, style: str = "body") -> float:
    para = p(text, style)
    _, height = para.wrap(width, 1000)
    para.drawOn(c, x, top - height)
    return top - height


def draw_bg(c: canvas.Canvas, page: int) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.035))
    c.setLineWidth(0.5)
    for x in range(0, int(W), 42):
        c.line(x, 0, x, H)
    for y in range(0, int(H), 42):
        c.line(0, y, W, y)
    c.setFillColor(DIM)
    c.setFont("Helvetica", 8)
    c.drawString(52, 24, "CineShield 2.0 - copyright threat intelligence brief")
    c.drawRightString(W - 52, 24, f"{page}/5")


def draw_card(c: canvas.Canvas, x: float, y: float, width: float, height: float, fill=SURFACE) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, y, width, height, 8, stroke=1, fill=1)


def draw_metric(c: canvas.Canvas, x: float, y: float, width: float, value: str, label: str, note: str) -> None:
    draw_card(c, x, y, width, 108)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 27)
    c.drawString(x + 16, y + 62, value)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 16, y + 43, label.upper())
    draw_para(c, note, x + 16, y + 34, width - 32, "small")


def draw_image_cover(c: canvas.Canvas, image_path: Path, x: float, y: float, width: float, height: float) -> None:
    draw_card(c, x, y, width, height, SURFACE)
    if not image_path.exists():
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x + width / 2, y + height / 2, "Screenshot not found")
        return

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        img_w, img_h = image.size

    scale = max(width / img_w, height / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale
    draw_x = x + (width - draw_w) / 2
    draw_y = y + (height - draw_h) / 2

    c.saveState()
    clip = c.beginPath()
    clip.roundRect(x, y, width, height, 8)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(ImageReader(str(image_path)), draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=False, mask="auto")
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.27))
    c.rect(x, y, width, height, stroke=0, fill=1)
    c.restoreState()


def draw_bullets(c: canvas.Canvas, items: Iterable[str], x: float, top: float, width: float, gap: float = 7) -> float:
    y = top
    for item in items:
        c.setFillColor(TEAL)
        c.circle(x + 4, y - 7, 3, stroke=0, fill=1)
        y = draw_para(c, item, x + 16, y, width - 16, "body") - gap
    return y


def draw_section_header(c: canvas.Canvas, eyebrow: str, title: str, subtitle: str = "") -> None:
    draw_para(c, eyebrow.upper(), 54, H - 56, 360, "eyebrow")
    title_bottom = draw_para(c, title, 54, H - 86, 690, "page_title")
    if subtitle:
        draw_para(c, subtitle, 54, title_bottom - 9, 650, "subhead")


def arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    c.line(x1, y1, x2, y2)
    c.setFillColor(GOLD)
    c.saveState()
    c.translate(x2, y2)
    c.rotate(0)
    c.line(-6, 4, 0, 0)
    c.line(-6, -4, 0, 0)
    c.restoreState()


def draw_arch_node(
    c: canvas.Canvas,
    center_x: float,
    center_y: float,
    label: str,
    width: float = 190,
    height: float = 30,
    fill=SURFACE_2,
    stroke=LINE,
) -> None:
    x = center_x - width / 2
    y = center_y - height / 2
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, width, height, 7, stroke=1, fill=1)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(center_x, center_y - 3, label)


def arrow_to(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, color=GOLD) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(1.35)
    c.line(x1, y1, x2, y2)
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    c.saveState()
    c.translate(x2, y2)
    c.rotate(angle)
    c.line(-5, 3, 0, 0)
    c.line(-5, -3, 0, 0)
    c.restoreState()


def slide_1(c: canvas.Canvas) -> None:
    draw_bg(c, 1)
    draw_para(c, "MAJOR PROJECT BRIEF", 54, H - 58, 360, "eyebrow")
    draw_para(c, "CineShield 2.0", 54, H - 98, 470, "title")
    draw_para(
        c,
        "An AI-powered copyright threat intelligence system for movies, web series, TV shows, OTT originals, clips, and other premium digital video.",
        54,
        H - 146,
        520,
        "subhead",
    )
    draw_metric(c, 54, H - 310, 170, "215B+", "Global piracy visits", "MUSO reports piracy website visits measured in 2024.")
    draw_metric(c, 239, H - 310, 170, "INR224B", "India piracy economy", "EY-IAMAI estimate for India in 2023.")
    draw_metric(
        c,
        424,
        H - 310,
        170,
        "63%",
        "Streaming share",
        "EY-IAMAI: streaming was 63% of pirated-content access sources in India.",
    )
    draw_para(
        c,
        "Problem: content is no longer copied only as a file. It appears as transformed streams, mirror uploads, cropped clips, subtitle edits, and platform-specific re-posts.",
        54,
        H - 358,
        520,
        "body",
    )
    draw_image_cover(c, SCREENSHOTS[0], 610, 86, 182, 154)
    draw_image_cover(c, SCREENSHOTS[1], 610, 258, 182, 154)
    draw_image_cover(c, SCREENSHOTS[2], 610, 430, 182, 104)
    draw_para(c, "Screenshots are used only as problem context examples.", 610, 76, 182, "small")


def slide_2(c: canvas.Canvas) -> None:
    draw_bg(c, 2)
    draw_section_header(
        c,
        "The idea",
        "Content DNA, not filename search",
        "A one-glance architecture for verifying transformed copies and turning results into review-ready evidence.",
    )

    cx = W / 2
    y_protected = H - 190
    y_dna = H - 230
    y_discovery = H - 270
    y_fingerprint = H - 310
    y_signals = H - 365
    y_fusion = H - 420
    y_decision = H - 472
    y_graph = H - 522

    main_nodes = [
        (y_protected, "PROTECTED MOVIE / EPISODE / CLIP", 270, TEAL),
        (y_dna, "CONTENT DNA", 214, GOLD),
        (y_discovery, "CANDIDATE DISCOVERY", 238, TEAL),
        (y_fingerprint, "VIDEO FINGERPRINTING", 238, TEAL),
    ]

    for index, (y, label, width, stroke) in enumerate(main_nodes):
        draw_arch_node(c, cx, y, label, width=width, height=30, stroke=stroke)
        if index < len(main_nodes) - 1:
            arrow_to(c, cx, y - 17, cx, main_nodes[index + 1][0] + 17)

    signal_nodes = [
        (cx - 180, "Visual", "frames"),
        (cx, "Audio", "sound"),
        (cx + 180, "Scene", "sequence"),
    ]
    for x, label, note in signal_nodes:
        draw_arch_node(c, x, y_signals, label, width=120, height=34, fill=SURFACE)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(x, y_signals - 22, note)
        arrow_to(c, cx, y_fingerprint - 17, x, y_signals + 19, TEAL)
        arrow_to(c, x, y_signals - 23, cx, y_fusion + 17, TEAL)

    draw_arch_node(c, cx, y_fusion, "EVIDENCE FUSION", width=230, height=34, stroke=GOLD)

    decision_nodes = [
        (cx - 172, "MATCH", JADE),
        (cx, "REVIEW", GOLD),
        (cx + 172, "REJECT", CORAL),
    ]
    for x, label, stroke in decision_nodes:
        draw_arch_node(c, x, y_decision, label, width=118, height=34, fill=SURFACE, stroke=stroke)
        arrow_to(c, cx, y_fusion - 19, x, y_decision + 19, stroke)
        arrow_to(c, x, y_decision - 19, cx, y_graph + 17, stroke)

    draw_arch_node(c, cx, y_graph, "THREAT GRAPH + EVIDENCE PACKAGE + HUMAN AUTHORIZATION", width=430, height=34, stroke=TEAL)


def slide_3(c: canvas.Canvas) -> None:
    draw_bg(c, 3)
    draw_section_header(
        c,
        "Example scenario",
        "An OTT episode leak becomes an evidence case",
        "The demo story can be explained without heavy technical language.",
    )
    draw_image_cover(c, SCREENSHOTS[2], 54, 128, 310, 210)
    draw_para(c, "Example: a released episode or show clip starts appearing on unauthorized viewing pages.", 54, 114, 310, "small")

    steps = [
        ("1. Register", "Rights holder uploads the original episode, show, trailer, or event video."),
        ("2. Generate DNA", "The system samples frame, scene, audio/temporal, and metadata signals."),
        ("3. Process candidates", "Uploaded files, partner feeds, or lawful URL queues become candidates."),
        ("4. Verify", "Transformed copies are scored using adaptive multimodal fusion."),
        ("5. Respond safely", "The output is an evidence package for human authorization."),
    ]
    x, top = 398, H - 170
    card_h = 54
    card_gap = 10
    for title, body in steps:
        draw_card(c, x, top - card_h, 370, card_h, SURFACE)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 16, top - 22, title)
        draw_para(c, body, x + 16, top - 36, 330, "small")
        top -= card_h + card_gap
    draw_para(
        c,
        "Important boundary: CineShield produces evidence and review priority. It does not declare legality or perform automatic takedowns.",
        398,
        86,
        370,
        "body_bold",
    )


def slide_4(c: canvas.Canvas) -> None:
    draw_bg(c, 4)
    draw_section_header(
        c,
        "Current build",
        "A real pipeline, not only a dashboard",
        "The UI is the command center; the backend processes local media and returns measured scan results.",
    )
    card_y = 92
    card_h = 318
    draw_card(c, 54, card_y, 344, card_h, SURFACE)
    draw_para(c, "Implemented now", 76, card_y + card_h - 28, 280, "body_bold")
    draw_bullets(
        c,
        [
            "Frontend upload flow for protected video and candidate videos",
            "FastAPI backend with /api/scan and /api/scan/demo",
            "OpenCV/NumPy fingerprint extraction from local media",
            "Adaptive comparison: visual, scene, temporal, duration, coverage",
            "Candidate ranking, confidence, reasons, and investigator summary",
            "Synthetic benchmark plus real-media smoke test",
        ],
        76,
        card_y + card_h - 62,
        292,
        5,
    )
    draw_card(c, 424, card_y, 344, card_h, SURFACE)
    draw_para(c, "Tech stack", 446, card_y + card_h - 28, 280, "body_bold")
    draw_bullets(
        c,
        [
            "Frontend: HTML, CSS, JavaScript dashboard",
            "Backend: Python FastAPI service",
            "Media engine: OpenCV, NumPy, frame sampling",
            "AI/ML: CV features plus adaptive evidence fusion",
            "Investigator: priority and uncertainty from structured evidence",
            "Safety: human review gate before response action",
        ],
        446,
        card_y + card_h - 62,
        292,
        5,
    )
    draw_para(
        c,
        "Demo path: upload original -> upload suspected copies -> scan -> rank -> inspect evidence -> generate review package.",
        54,
        72,
        714,
        "body_bold",
    )


def slide_5(c: canvas.Canvas) -> None:
    draw_bg(c, 5)
    draw_section_header(
        c,
        "Roadmap",
        "Discovery connects into the same DNA engine",
        "The next stage is not rebuilding verification. It is adding lawful source connectors and queue-based monitoring.",
    )
    draw_card(c, 54, 296, 714, 122, SURFACE)
    stages = [
        ("Phase 1", "Local scanner and benchmarks"),
        ("Phase 2", "Discovery connector + candidate queue"),
        ("Phase 3", "Threat graph and monitoring"),
        ("Phase 4", "Partner integrations and audit trails"),
    ]
    for index, (title, body) in enumerate(stages):
        x = 80 + index * 168
        c.setFillColor(TEAL if index < 2 else GOLD)
        c.circle(x, 362, 9, stroke=0, fill=1)
        if index < len(stages) - 1:
            c.setStrokeColor(LINE)
            c.line(x + 12, 362, x + 150, 362)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x - 24, 336, title)
        draw_para(c, body, x - 24, 320, 130, "small")

    draw_card(c, 54, 132, 344, 142, SURFACE)
    draw_para(c, "Not implemented yet", 76, 246, 280, "body_bold")
    draw_bullets(
        c,
        [
            "Internet-wide discovery at scale",
            "Continuous external monitoring",
            "Production takedown integrations",
            "Automated legal decisions",
        ],
        76,
        218,
        290,
        2,
    )
    draw_card(c, 424, 132, 344, 142, SURFACE)
    draw_para(c, "Expected outcome", 446, 246, 280, "body_bold")
    draw_para(
        c,
        "A practical content-protection system that can help rights holders identify transformed video copies, prioritize review, and preserve an audit trail for safe action.",
        446,
        218,
        286,
        "body",
    )
    draw_para(
        c,
        "Sources: MUSO Piracy by Industry, EY-IAMAI The Rob Report press release, FICCI-EY India M&E report, U.S. Chamber copyright report. The 63% metric refers to streaming's share among pirated-content access sources in India. Screenshots supplied by project owner as problem context.",
        54,
        86,
        714,
        "small",
    )


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(A4))
    for maker in [slide_1, slide_2, slide_3, slide_4, slide_5]:
        maker(c)
        c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    build()
