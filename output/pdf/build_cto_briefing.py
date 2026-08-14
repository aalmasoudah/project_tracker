# ruff: noqa: E501
# Document copy is intentionally kept as complete strings for ReportLab flowables.

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "insight-tracker-complete-cto-guide.pdf"
LOGO = ROOT / "static" / "img" / "insight-tracker-logo.png"
MARK = ROOT / "static" / "img" / "insight-tracker-mark.png"
FONT = (
    ROOT / "static" / "vendor" / "fonts" / "NotoSansArabic-VariableFont_wdth,wght.ttf"
)
ASSETS = ROOT / "output" / "presentation" / "assets"

DEEP = colors.HexColor("#0A400C")
FOREST = colors.HexColor("#17531B")
SAGE = colors.HexColor("#819067")
STONE = colors.HexColor("#B1AB86")
PAPER = colors.HexColor("#F3F1E8")
INK = colors.HexColor("#243127")
MUTED = colors.HexColor("#667067")
LINE = colors.HexColor("#D8DBD0")
WHITE = colors.white


def rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


pdfmetrics.registerFont(TTFont("NotoArabic", str(FONT)))


class Rule(Flowable):
    def __init__(
        self, width: float, color: colors.Color = STONE, thickness: float = 2.0
    ):
        super().__init__()
        self.width = width
        self.height = thickness
        self.color = color
        self.thickness = thickness

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


class CroppedImage(Flowable):
    """Render a window into a tall application screenshot without distortion."""

    def __init__(
        self,
        path: Path,
        width: float,
        height: float,
        vertical_focus: float,
    ) -> None:
        super().__init__()
        self.path = path
        self.width = width
        self.height = height
        self.vertical_focus = min(1.0, max(0.0, vertical_focus))

    def draw(self) -> None:
        with PILImage.open(self.path) as source:
            source_ratio = source.height / source.width
        draw_height = self.width * source_ratio
        overflow = max(0.0, draw_height - self.height)
        y_position = -(overflow * self.vertical_focus)
        clip = self.canv.beginPath()
        clip.rect(0, 0, self.width, self.height)
        self.canv.saveState()
        self.canv.clipPath(clip, stroke=0, fill=0)
        self.canv.drawImage(
            str(self.path),
            0,
            y_position,
            width=self.width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.canv.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "CoverKicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#DCE1D2"),
        spaceAfter=13,
        tracking=1.4,
    )
)
styles.add(
    ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=34,
        leading=36,
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceAfter=15,
    )
)
styles.add(
    ParagraphStyle(
        "CoverLead",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=13.5,
        leading=19,
        textColor=colors.HexColor("#E6E9DF"),
        spaceAfter=13,
    )
)
styles.add(
    ParagraphStyle(
        "CoverArabic",
        parent=styles["BodyText"],
        fontName="NotoArabic",
        fontSize=17,
        leading=22,
        textColor=WHITE,
        alignment=TA_RIGHT,
    )
)
styles.add(
    ParagraphStyle(
        "Kicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        textColor=FOREST,
        spaceAfter=6,
        tracking=1.1,
    )
)
styles.add(
    ParagraphStyle(
        "H1Brand",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=27,
        textColor=DEEP,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        "H2Brand",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=16,
        textColor=DEEP,
        spaceBefore=5,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "BodyBrand",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.3,
        leading=13.3,
        textColor=INK,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "BodySmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.1,
        leading=11.2,
        textColor=MUTED,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        "BulletBrand",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.9,
        leading=12.5,
        leftIndent=13,
        firstLineIndent=-8,
        bulletIndent=0,
        textColor=INK,
        spaceAfter=4.5,
    )
)
styles.add(
    ParagraphStyle(
        "CalloutTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=WHITE,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "CalloutBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.4,
        leading=13.7,
        textColor=colors.HexColor("#EDF0E8"),
    )
)
styles.add(
    ParagraphStyle(
        "TableHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.7,
        leading=9.2,
        textColor=WHITE,
    )
)
styles.add(
    ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.5,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        "Q",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=12.4,
        textColor=DEEP,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        "A",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.4,
        textColor=INK,
    )
)


def p(text: str, style: str = "BodyBrand") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", styles["BulletBrand"])


def title(kicker: str, heading: str, lead: str | None = None) -> list[Flowable]:
    items: list[Flowable] = [p(kicker.upper(), "Kicker"), p(heading, "H1Brand")]
    if lead:
        items.append(p(lead, "BodyBrand"))
    items.extend([Spacer(1, 3 * mm), Rule(180 * mm), Spacer(1, 5 * mm)])
    return items


def screenshot(path: Path, width: float, caption: str) -> Table:
    with PILImage.open(path) as source:
        ratio = source.height / source.width
    image = Image(str(path), width=width, height=width * ratio)
    frame = Table([[image], [p(caption, "BodySmall")]], colWidths=[width + 4 * mm])
    frame.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEABOVE", (0, 1), (-1, 1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    return frame


def screenshot_window(
    path: Path,
    width: float,
    height: float,
    caption: str,
    *,
    vertical_focus: float,
) -> Table:
    image = CroppedImage(path, width, height, vertical_focus)
    frame = Table([[image], [p(caption, "BodySmall")]], colWidths=[width + 4 * mm])
    frame.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEABOVE", (0, 1), (-1, 1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    return frame


def callout(heading: str, text: str, width: float = 180 * mm) -> Table:
    inner = [p(heading, "CalloutTitle"), p(text, "CalloutBody")]
    table = Table([[inner]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DEEP),
                ("BOX", (0, 0), (-1, -1), 0, DEEP),
                ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6 * mm),
            ]
        )
    )
    return table


def qa(question: str, answer: str) -> Table:
    block = Table([[p(question, "Q")], [p(answer, "A")]], colWidths=[85 * mm])
    block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF6")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2 * mm),
            ]
        )
    )
    return block


def draw_contained(
    canvas: Canvas, path: Path, x: float, y: float, width: float, height: float
) -> None:
    with PILImage.open(path) as image:
        source_ratio = image.width / image.height
    target_ratio = width / height
    if source_ratio > target_ratio:
        draw_width = width
        draw_height = width / source_ratio
    else:
        draw_height = height
        draw_width = height * source_ratio
    canvas.drawImage(
        str(path),
        x + (width - draw_width) / 2,
        y + (height - draw_height) / 2,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )


def page_decor(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    page_width, page_height = A4
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(DEEP)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        canvas.setFillColor(FOREST)
        canvas.circle(
            page_width + 12 * mm, page_height + 2 * mm, 78 * mm, fill=1, stroke=0
        )
        canvas.setFillColor(colors.HexColor("#2E6530"))
        canvas.circle(
            page_width + 20 * mm, page_height - 10 * mm, 49 * mm, fill=1, stroke=0
        )
        canvas.setFillColor(WHITE)
        canvas.roundRect(
            page_width - 76 * mm,
            page_height - 93 * mm,
            54 * mm,
            54 * mm,
            7 * mm,
            fill=1,
            stroke=0,
        )
        draw_contained(
            canvas, LOGO, page_width - 69 * mm, page_height - 87 * mm, 40 * mm, 42 * mm
        )
        canvas.setStrokeColor(colors.HexColor("#8EA77F"))
        canvas.setLineWidth(1.5)
        canvas.line(18 * mm, 18 * mm, page_width - 18 * mm, 18 * mm)
        canvas.setFillColor(colors.HexColor("#DCE1D2"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            18 * mm,
            10.8 * mm,
            "Insight Tracker - internal CTO briefing - 4 August 2026",
        )
    else:
        canvas.setFillColor(DEEP)
        canvas.rect(0, page_height - 7 * mm, page_width, 7 * mm, fill=1, stroke=0)
        draw_contained(canvas, MARK, 16 * mm, page_height - 18 * mm, 13 * mm, 8 * mm)
        canvas.setFillColor(DEEP)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(31 * mm, page_height - 14.8 * mm, "INSIGHT TRACKER")
        canvas.setFont("NotoArabic", 8.8)
        canvas.drawRightString(
            page_width - 18 * mm, page_height - 14.8 * mm, rtl("إنسايت تراكر")
        )
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(18 * mm, 14 * mm, page_width - 18 * mm, 14 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.8)
        canvas.drawString(18 * mm, 8 * mm, "CTO briefing - internal pilot discussion")
        canvas.drawRightString(page_width - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def table(data: list[list[str]], widths: list[float], header: bool = True) -> Table:
    converted: list[list[Paragraph]] = []
    for row_index, row in enumerate(data):
        style = "TableHead" if header and row_index == 0 else "TableCell"
        converted.append([p(cell, style) for cell in row])
    result = Table(
        converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT"
    )
    directives = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]
    if header:
        directives.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DEEP),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [WHITE, colors.HexColor("#F7F6F0")],
                ),
            ]
        )
    result.setStyle(TableStyle(directives))
    return result


def cards(items: Iterable[tuple[str, str]], columns: int = 2) -> Table:
    cells = []
    for heading, text in items:
        cells.append([p(heading, "H2Brand"), p(text, "BodySmall")])
    rows = [cells[index : index + columns] for index in range(0, len(cells), columns)]
    if rows and len(rows[-1]) < columns:
        rows[-1].extend([[] for _ in range(columns - len(rows[-1]))])
    width = 176 * mm / columns
    result = Table(rows, colWidths=[width] * columns, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF6")),
                ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.55, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return result


story: list[Flowable] = []

# 1 - Cover
story.extend(
    [
        Spacer(1, 28 * mm),
        p("15-MINUTE INTERNAL CTO BRIEFING", "CoverKicker"),
        p("Insight Tracker", "CoverTitle"),
        Table(
            [
                [
                    p(
                        "A secure, Arabic-first workspace from program plan to verified result.",
                        "CoverLead",
                    )
                ]
            ],
            colWidths=[100 * mm],
            hAlign="LEFT",
            style=TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        ),
        Spacer(1, 8 * mm),
        p(rtl("إنسايت تراكر"), "CoverArabic"),
        Spacer(1, 55 * mm),
        p(
            "Complete feature guide, AI governance, technical posture, likely CTO questions, test evidence, presentation script, and pilot recommendation.",
            "CoverLead",
        ),
        Spacer(1, 8 * mm),
        callout(
            "Recommended decision",
            "Approve a controlled pilot for one program using fictional or anonymized data. Production use remains gated by university security, data-residency, operational ownership, and restore-test approval.",
            width=118 * mm,
        ),
        PageBreak(),
    ]
)

# 2 - Executive overview
story.extend(
    title(
        "Executive overview",
        "What the product is - and why the university would use it",
    )
)
overview_text = [
    p(
        "Insight Tracker is a Django and PostgreSQL application that centralizes programs, projects, courses, tasks, people, attendance, approvals, evidence, notifications, dashboards, and exports in one permission-controlled workspace."
    ),
    bullet(
        "Leadership sees current progress, overdue work, approval status, and operational evidence without waiting for manually assembled updates."
    ),
    bullet(
        "Delivery teams work from one hierarchy with explicit ownership and a durable activity trail."
    ),
    bullet(
        "Arabic is a first-class interface and reporting language; English is available with direction-aware RTL/LTR behavior."
    ),
    bullet("Important business records are archived instead of silently deleted."),
]
overview_table = Table(
    [
        [
            overview_text,
            screenshot(
                ASSETS / "dashboard-ar.png",
                83 * mm,
                "Real Arabic demo dashboard with seven projects and 42 tasks.",
            ),
        ]
    ],
    colWidths=[86 * mm, 90 * mm],
)
overview_table.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ]
    )
)
story.extend(
    [
        overview_table,
        Spacer(1, 6 * mm),
        callout(
            "One-sentence answer",
            '"It is an internal delivery-control platform that connects the plan, the people, the approvals, and the evidence in Arabic and English."',
        ),
        PageBreak(),
    ]
)

# 3 - Demo scenario
story.extend(
    title(
        "Fictional university scenario",
        "How programs, projects, tasks, and shared workers fit together",
    )
)
scenario = [
    ["Program", "Example projects", "People model"],
    [
        "KAU digital services",
        "Smart Student Services Portal; Academic Analytics Platform",
        "KAU specialists plus a shared coordinator and shared analyst",
    ],
    [
        "KSU research enablement",
        "Research Innovation Incubator; Laboratory Management Platform",
        "KSU specialists plus the same cross-program resources",
    ],
    [
        "KKU student experience",
        "Student Journey Application; Digital Support Center",
        "KKU specialists plus shared roles where authorized",
    ],
]
story.extend(
    [
        table(scenario, [40 * mm, 72 * mm, 64 * mm]),
        Spacer(1, 5 * mm),
        p(
            "The demo data is fictional. It is designed to prove that the same task pattern can repeat across projects while project-specific work and membership remain separate."
        ),
        screenshot(
            ASSETS / "projects-ar.png",
            165 * mm,
            "Real Arabic project register showing fictional KAU, KSU, and KKU projects.",
        ),
        Spacer(1, 2 * mm),
        callout(
            "What to demonstrate",
            "Open the project register, select KAU's Smart Student Services Portal, point out the bilingual name, client, category, project manager, supervisor, priority, team, progress, budget, dates, and approval action.",
        ),
        PageBreak(),
    ]
)

# 4 - Workflow and roles
story.extend(title("Operating workflow", "What each team member experiences"))
flow = [
    ["Step", "Actor", "System behavior"],
    [
        "1. Plan",
        "Executive / Project Manager",
        "Create the project, team, tasks, milestones, dates, priority, and responsibilities.",
    ],
    [
        "2. Execute",
        "Employee / Contractor",
        "Update assigned work, progress, comments, tags, and permitted evidence.",
    ],
    [
        "3. Review",
        "Supervisor",
        "Review first-stage completion and approve or reject with a recorded reason.",
    ],
    [
        "4. Approve",
        "Project Manager",
        "Provide the second independent decision. The same person cannot approve both stages.",
    ],
    [
        "5. Govern",
        "Executive / authorized roles",
        "View dashboard, overdue work, audit records, and scoped PDF/XLSX reports.",
    ],
]
story.extend([table(flow, [21 * mm, 39 * mm, 116 * mm]), Spacer(1, 6 * mm)])
role_cards = [
    (
        "Technical Administrator",
        "Manages technical configuration and internal accounts; not a shortcut around object permissions.",
    ),
    (
        "CEO / Executive Manager",
        "Portfolio-level visibility and governance according to granted scope.",
    ),
    (
        "Project Manager / Supervisor",
        "Own project delivery and perform distinct approval stages.",
    ),
    (
        "Employee / Contractor",
        "Work within assigned projects and tasks; direct URL checks still enforce access.",
    ),
    (
        "External Trainer",
        "Uses a random, expiring, session-scoped capability link for attendance only.",
    ),
    (
        "Concurrent work",
        "Multiple users can use separate devices at the same time; transactions and database constraints protect critical writes. Final capacity still needs load testing.",
    ),
]
story.extend(
    [
        cards(role_cards),
        Spacer(1, 6 * mm),
        callout(
            "Approval rule to remember",
            "Supervisor first, Project Manager second. One actor cannot complete both stages. Rejections require a reason, retries are preserved, and history is not rewritten.",
        ),
        PageBreak(),
    ]
)

# 5 - Capabilities
story.extend(title("Product capability", "What is already implemented"))
capabilities = [
    (
        "Program delivery",
        "Projects, departments, clients, categories, courses, tasks, milestones, teams, progress, archives, Kanban, calendar, timeline, and Gantt views.",
    ),
    (
        "People and attendance",
        "Internal users, trainees, imports, sessions, trainer links, submission, review, correction, and aggregate attendance reporting.",
    ),
    (
        "Governance",
        "Sequential approvals, append-only audit history, scoped search, notifications, operational archive and restore flows.",
    ),
    (
        "Reports",
        "Project progress, overdue tasks, and attendance summaries in PDF/XLSX; Arabic or English; Gregorian and Hijri dates with Western digits.",
    ),
]
story.extend([cards(capabilities), Spacer(1, 6 * mm)])
cap_screen_table = Table(
    [
        [
            screenshot(
                ASSETS / "project-detail-ar.png",
                84 * mm,
                "KAU project detail and team controls.",
            ),
            screenshot(
                ASSETS / "reports-ar.png", 84 * mm, "Arabic PDF/XLSX report center."
            ),
        ]
    ],
    colWidths=[88 * mm, 88 * mm],
)
cap_screen_table.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ]
    )
)
story.extend(
    [
        cap_screen_table,
        Spacer(1, 4 * mm),
        p(
            "Export safeguards: at most 5,000 rows, at most a 366-day range, aggregate attendance only, permission-scoped rows, spreadsheet formula neutralization, no persistent generated-file URL, and no-store responses.",
            "BodySmall",
        ),
        PageBreak(),
    ]
)

# 6 - Phase 15 AI briefing
story.extend(
    title(
        "New AI capability - Phase 15",
        "Cited project briefings without autonomous action",
    )
)
ai_briefing_row = Table(
    [
        [
            screenshot_window(
                ASSETS / "ai-briefing-ar.png",
                76 * mm,
                58 * mm,
                "Arabic deterministic AI briefing with links to visible evidence.",
                vertical_focus=0.28,
            ),
            [
                p("What it does", "H2Brand"),
                bullet(
                    "Builds a bounded evidence bundle from project status, progress, tasks, milestones, approvals, and recent activity."
                ),
                bullet(
                    "Returns a strict summary, highlights, risks, upcoming items, recommendations, and data gaps."
                ),
                bullet(
                    "Requires citations for factual statements and links only to records the current user can view."
                ),
                p("What it cannot do", "H2Brand"),
                bullet("No tools, writes, shell, SQL, files, arbitrary URLs, or chat."),
                bullet(
                    "It cannot approve completion, change a task, send a notification, or create an autonomous workflow."
                ),
                p("Provider and token efficiency", "H2Brand"),
                bullet(
                    "Groq defaults to openai/gpt-oss-120b; openai/gpt-oss-20b is an explicit lower-cost override."
                ),
                bullet(
                    "Bounded evidence, fingerprints, prompt versions, token metrics, cached-input metrics, and a deterministic fake provider control cost and testing."
                ),
            ],
        ]
    ],
    colWidths=[82 * mm, 94 * mm],
)
ai_briefing_row.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ]
    )
)
story.extend(
    [
        ai_briefing_row,
        Spacer(1, 5 * mm),
        callout(
            "How to explain it",
            '"The AI helps leadership read the existing evidence faster. It does not create new authority, and every important claim remains reviewable against the source record."',
        ),
        PageBreak(),
    ]
)

# 7 - Phase 16 CEO Telegram and n8n
story.extend(
    title(
        "New executive channel - Phase 16",
        "Secure fixed Arabic briefings through Telegram and n8n",
    )
)
telegram_flow = [
    ["Step", "Owner", "Control"],
    [
        "1. Fixed command",
        "CEO in private Telegram chat",
        "/help, /tasks, /overdue, or /attendance only; no unrestricted chat.",
    ],
    [
        "2. Route",
        "Inactive n8n workflow",
        "Rejects other chats and signs the exact method, path, body, timestamp, and one-use nonce.",
    ],
    [
        "3. Authorize",
        "Django",
        "Rechecks the configured active CEO, role, permission, chat binding, schema, and request bounds.",
    ],
    [
        "4. Generate",
        "Django and approved AI boundary",
        "Creates an Arabic summary or branded PDF. Groq receives aggregate attendance evidence only.",
    ],
    [
        "5. Deliver",
        "n8n and Telegram",
        "Uses a short-lived one-time PDF link, safe audit event, and deduplicated critical-task alerts.",
    ],
]
story.extend([table(telegram_flow, [30 * mm, 47 * mm, 99 * mm]), Spacer(1, 6 * mm)])
story.extend(
    [
        cards(
            [
                (
                    "Data minimization",
                    "Trainee names and attendance values are included only in the explicitly requested CEO PDF. Phone, email, and notes stay excluded; Groq receives aggregates only.",
                ),
                (
                    "Credential boundary",
                    "n8n has no database or Redis credential. Telegram uses its native credential store, and HMAC values come from deployment secrets.",
                ),
                (
                    "Failure safety",
                    "Nonce replay, expired signatures, wrong chats, oversized bodies, duplicate alerts, failed delivery, and retry leases are tested and audited safely.",
                ),
                (
                    "Activation status",
                    "The workflow ships inactive and credential-free. A dedicated staging bot, public HTTPS endpoint, secrets, retention review, and privacy UAT are required.",
                ),
            ]
        ),
        Spacer(1, 6 * mm),
        callout(
            "How to explain it",
            '"Telegram is only a convenient executive channel. Django remains the security and reporting authority; n8n routes and delivers but cannot query or edit the application database."',
        ),
        PageBreak(),
    ]
)

# 8 - Phase 17 project recovery agent
story.extend(
    title(
        "New governed agent - Phase 17",
        "Goal-driven recovery planning with human approval and final verification",
    )
)
agent_flow = [
    ["Stage", "Guarded behavior", "Acceptance proof"],
    [
        "1. Plan",
        "Validate the user, project, predefined recovery goal, step/time/token limits, and daily quota.",
        "A bounded plan is stored before any tool call.",
    ],
    [
        "2. Observe",
        "Dynamically select only approved project snapshot, task, milestone, approval, workload, progress, or reviewed-memory reads.",
        "At least two tools run; the first observation changes the next selection.",
    ],
    [
        "3. Propose",
        "Create a cited task update, assignment, comment, deadline, or team-notification proposal; never write directly.",
        "The run pauses in awaiting approval and source data is unchanged.",
    ],
    [
        "4. Decide",
        "Require a human reason and recheck current permission, scope, expiry, lifecycle, and before-state fingerprint.",
        "Rejected, unauthorized, revoked, expired, or stale actions make no write.",
    ],
    [
        "5. Execute",
        "Reuse existing transactional domain services with an idempotency key and duplicate-worker protection.",
        "An approved action executes once without bypassing completion approvals.",
    ],
    [
        "6. Verify",
        "Read the actual post-action state and create a bounded cited final report; reviewed runs may enter project memory.",
        "The eighth step proves the final state and its source reference.",
    ],
]
story.extend(
    [
        table(agent_flow, [25 * mm, 87 * mm, 64 * mm]),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "Reviewed memory only",
                    "Only an explicitly reviewed completed run can inform a later authorized run on the same project.",
                ),
                (
                    "Concurrency safety",
                    "Worker claims, bounded retries, cancellation, stale recovery, row locks, fingerprints, and idempotency prevent partial or duplicate effects.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "Strongest safety answer",
            "The agent has no shell, raw SQL, filesystem, web search, arbitrary HTTP, code execution, credentials, files, trainee, attendance, or raw-audit tools. Prompt text cannot create a new tool or bypass the approval checkpoint.",
        ),
        PageBreak(),
    ]
)

# 9 - Architecture
story.extend(
    title(
        "Technical architecture",
        "A maintainable monolith with clear production boundaries",
    )
)
architecture = [
    ["Layer", "Technology / responsibility", "Why it matters"],
    [
        "Web application",
        "Django 5.2 LTS, Python 3.13, Django Templates, Bootstrap 5, HTMX",
        "Simple server-rendered architecture with fewer moving parts and first-class localization.",
    ],
    [
        "Data",
        "PostgreSQL in development, test, staging, and production",
        "Transactions, constraints, indexes, durable relational integrity, and scoped queries.",
    ],
    [
        "Background work",
        "Celery 5 and Redis 8 when background processing is required",
        "Separates notifications or longer work from interactive requests.",
    ],
    [
        "Runtime",
        "Docker / Compose locally; Gunicorn for production",
        "Repeatable packaging and a portable hosting target.",
    ],
    [
        "Files",
        "Local private storage in development; S3-compatible private storage in production",
        "Avoids public-by-default evidence files and supports controlled delivery.",
    ],
    [
        "Observability",
        "Structured logs, request correlation, health checks, audit records",
        "Supports diagnosis without exposing stack traces or raw sensitive metadata.",
    ],
]
story.extend([table(architecture, [32 * mm, 70 * mm, 74 * mm]), Spacer(1, 7 * mm)])
story.extend(
    [
        cards(
            [
                (
                    "Deployment stance",
                    "The application is portable. Render is documented as a target, but the university must approve provider, region, plan, domain, network posture, and data residency.",
                ),
                (
                    "Scalability answer",
                    "The web tier can be replicated and the database/background workers scaled, but university-scale concurrency has not yet been load-tested. A pilot supplies realistic usage assumptions.",
                ),
                (
                    "Integration stance",
                    "The current release is a monolith, not an integration marketplace. SSO, institutional systems, and API integration should be explicitly scoped after the pilot.",
                ),
                (
                    "Maintenance stance",
                    "Domain apps, thin views, service-layer workflows, migrations, typed interfaces, and automated tests keep change risk understandable.",
                ),
            ]
        ),
        Spacer(1, 6 * mm),
        callout(
            "Honest architecture answer",
            '"The architecture is ready for a controlled pilot. Production topology and integrations are decisions to complete with university infrastructure and security teams, not assumptions hidden inside the demo."',
        ),
        PageBreak(),
    ]
)

# 7 - Security and Arabic
story.extend(
    title(
        "Security, privacy, and Arabic",
        "Controls already present - and controls still required before launch",
    )
)
security_cards = [
    (
        "Access control",
        "Authenticated sessions, active-account checks, role plus object-level authorization, method checks, CSRF protection, and permission-scoped exports.",
    ),
    (
        "Sensitive workflows",
        "Database transactions for approvals/imports, immutable approval history, randomized expiring trainer links, hashed tokens where practical, and replay/expiry checks.",
    ),
    (
        "Data protection",
        "Validated upload size/extension/MIME, private production object storage, no production DEBUG, secrets from environment variables, no raw sensitive audit export.",
    ),
    (
        "Arabic quality",
        "Arabic is preserved, not destructively normalized. Search uses approved normalization. RTL/LTR, mixed content, Unicode round-trip, PDFs, XLSX, and Hijri/Gregorian rendering are verified.",
    ),
]
story.extend([cards(security_cards), Spacer(1, 6 * mm)])
audit_row = Table(
    [
        [
            screenshot(
                ASSETS / "audit-ar.png",
                87 * mm,
                "Arabic append-only, permission-scoped audit view.",
            ),
            [
                p("Operational targets", "H2Brand"),
                bullet("Backup target: RPO 24 hours and RTO 8 hours."),
                bullet("Encrypted backup retention target: 35 days."),
                bullet("Quarterly isolated restore exercise is required."),
                bullet(
                    "Application data retention is indefinite for the initial release unless policy changes."
                ),
                Spacer(1, 3 * mm),
                p("Not yet claimed", "H2Brand"),
                bullet("No real production backup has been created or restored."),
                bullet("No production provider/region/data-residency approval yet."),
                bullet(
                    "Named operational owners and alert routes remain a launch gate."
                ),
            ],
        ]
    ],
    colWidths=[92 * mm, 84 * mm],
)
audit_row.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ]
    )
)
story.extend([audit_row, PageBreak()])

# 8 - Testing
story.extend(
    title(
        "Verification evidence",
        "What was tested, what passed, and what has not been claimed",
    )
)
results = [
    ["Evidence", "Latest verified result", "Coverage"],
    [
        "Automated non-browser",
        "200 passed",
        "Models, constraints, selectors, forms, permissions, services, transactions, reports, AI schemas, retries, security cases, imports, and integrations.",
    ],
    [
        "Playwright browser",
        "16 passed",
        "Critical Arabic RTL and English LTR journeys, permissions, reports, AI workflows, and responsive/mobile behavior in installed Google Chrome.",
    ],
    [
        "Total test suite",
        "216 passed",
        "Latest complete local quality gate executed on 2026-08-04: 200 non-browser plus 16 browser workflows.",
    ],
    [
        "Static quality",
        "Passed",
        "Ruff formatting/checks; mypy across 281 source files; Django system checks; no migration drift; Git diff validation.",
    ],
    [
        "Localization",
        "Passed",
        "1,173 Arabic messages compiled with 0 untranslated; Arabic round-trip, mixed content, RTL/LTR, Hijri/Gregorian output.",
    ],
    [
        "Manual artifact QA",
        "Passed",
        "Application/report PDFs and the presentation guide were rendered and visually inspected; Excel and Arabic/English outputs checked.",
    ],
]
story.extend([table(results, [38 * mm, 37 * mm, 101 * mm]), Spacer(1, 5 * mm)])
test_cards = [
    (
        "Unit tests",
        "Pure business rules, formulas, validators, token utilities, invalid/boundary cases, archived state, and retry behavior.",
    ),
    (
        "Integration tests",
        "Django views/templates, PostgreSQL constraints and transactions, object permissions, imports, report policies, query-count and security boundaries.",
    ),
    (
        "Browser tests",
        "Real user journeys with Playwright across Arabic/English and representative responsive viewport behavior.",
    ),
    (
        "Security tests",
        "Anonymous/inactive/wrong-role/wrong-object access, prompt injection, forged IDs, stale state, revoked access, HMAC replay, duplicate execution, uploads, token expiry, sensitive logs, and spreadsheet formula injection.",
    ),
]
story.extend(
    [
        cards(test_cards),
        Spacer(1, 5 * mm),
        callout(
            "Do not overclaim",
            "Formal penetration testing, university-scale load testing, disaster-recovery restoration, provider security review, dependency/vulnerability scans at release time, and production UAT remain required before live launch.",
        ),
        PageBreak(),
    ]
)

# CTO questions - AI and automation
story.extend(
    title(
        "Likely CTO questions about AI",
        "Concise answers for the briefing, Telegram channel, and recovery agent",
    )
)
ai_qa_items = [
    (
        "Why use an LLM here?",
        "The useful role is synthesis and recovery planning across already-authorized evidence. Deterministic services still calculate progress, enforce permissions, execute changes, and verify state.",
    ),
    (
        "Can the model change records by itself?",
        "No. Phase 15 is read-only. Phase 17 can only create a validated proposal, pauses for a human, then Django rechecks permission and stale state before an existing domain service executes once.",
    ),
    (
        "How do we prevent hallucinated reports?",
        "Provider output must match strict schemas, factual items need valid citations, unknown references are rejected, and the UI tells users to verify the cited evidence before decision use.",
    ),
    (
        "What data is sent to Groq?",
        "Only bounded, permission-scoped evidence needed for the selected report or project goal. Secrets, credentials, files, raw audit metadata, trainee contact details, and attendance notes are excluded.",
    ),
    (
        "How are token costs controlled?",
        "Inputs are bounded and fingerprinted, tool results are size-limited, steps and total tokens are capped, daily requests are limited, cached-input metrics are recorded, and 20B is an explicit cost override.",
    ),
    (
        "Can prompt injection unlock tools?",
        "No. Database text is treated as untrusted data. Tool codes and arguments must pass exact schemas and project scope checks; unavailable tools, forged IDs, URLs, shell, SQL, and credential requests fail closed.",
    ),
    (
        "Why is n8n safe?",
        "It has no database credential and no business-write API. Fixed routes use HMAC, timestamps, one-use nonces, idempotency, and exact CEO chat binding; the workflow is inactive until staging approval.",
    ),
    (
        "What remains before live AI use?",
        "Groq and n8n secrets in a manager, approved data-processing and residency posture, staging prompt/security evaluation, privacy UAT, monitoring ownership, and an explicit production activation decision.",
    ),
]
ai_qa_rows = []
for index in range(0, len(ai_qa_items), 2):
    ai_qa_rows.append([qa(*ai_qa_items[index]), qa(*ai_qa_items[index + 1])])
ai_qa_table = Table(ai_qa_rows, colWidths=[89 * mm, 89 * mm], hAlign="LEFT")
ai_qa_table.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ]
    )
)
story.extend([ai_qa_table, PageBreak()])

# General CTO questions
story.extend(
    title("Likely CTO questions", "Concise answers you can use in the meeting")
)
qa_items = [
    (
        "Why build this instead of using Jira, Microsoft Project, or Asana?",
        "This is a domain-specific internal workflow that combines project delivery, courses, trainee attendance, two-stage approvals, Arabic reporting, and university-specific access in one controlled model. The pilot should prove where this consolidation adds value; it does not need to replace every specialist tool on day one.",
    ),
    (
        "Where will the data be hosted, and does it meet Saudi data-residency requirements?",
        "The application is portable and containerized, but the final provider, Saudi region, network model, and data-residency position are not assumed. Those are explicit university decisions before real data is used.",
    ),
    (
        "Does it support our SSO or identity provider?",
        "The current release uses secure internal Django accounts. Institutional SSO is not claimed as complete. We can scope SAML/OIDC integration with the university IdP after confirming its standards, role mapping, lifecycle rules, and MFA requirements.",
    ),
    (
        "Can many users work at the same time?",
        "Yes, separate devices and sessions can work concurrently, and critical writes use PostgreSQL transactions and constraints. The precise safe capacity has not been claimed; a realistic load test is a pre-production gate.",
    ),
    (
        "How do you stop users from seeing another program?",
        "Every protected view and export applies role and object-level scope. Direct URLs are checked, not just hidden in navigation. Tests cover anonymous, wrong-role, wrong-object, and cross-scope attempts.",
    ),
    (
        "Can records be deleted or the audit trail rewritten?",
        "Important records use archive/restore workflows. Approval history is immutable and audit records are append-only by design. Exported audit data is deliberately sanitized.",
    ),
    (
        "How are backups and disaster recovery handled?",
        "The documented target is encrypted backups with a 24-hour RPO, 8-hour RTO, 35-day backup retention, and quarterly isolated restore tests. A real provider backup and successful restore evidence are mandatory before launch.",
    ),
    (
        "Is Arabic truly supported or only translated labels?",
        "Arabic is first-class: RTL layout, preserved Unicode text, approved search normalization, mixed Arabic/English behavior, Arabic PDF/XLSX, and Hijri plus Gregorian dates were tested. English remains available with LTR layout.",
    ),
]
qa_rows = []
for index in range(0, len(qa_items), 2):
    qa_rows.append([qa(*qa_items[index]), qa(*qa_items[index + 1])])
qa_table = Table(qa_rows, colWidths=[89 * mm, 89 * mm], hAlign="LEFT")
qa_table.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]
    )
)
story.extend([qa_table, PageBreak()])

# 10 - More Q&A and pilot
story.extend(
    title(
        "Decision and next steps",
        "How to answer remaining questions and close the meeting",
    )
)
remaining_qa = [
    (
        "Is it production-ready today?",
        "Phases 1 through 17 are complete and verified locally. Approved for live university data, not yet. Production requires hosting/data-residency approval, SSO and provider decisions, secret and storage configuration, vulnerability scanning, AI/privacy UAT, monitoring ownership, real backup restoration, load testing, and role-based UAT.",
    ),
    (
        "What about mobile?",
        "It is a responsive web application tested at representative mobile viewports. It is not a native iOS or Android application.",
    ),
    (
        "Can we integrate with university systems?",
        "The architecture can support scoped integrations, but no specific SIS, HR, LMS, email, or SSO integration should be promised until interfaces, ownership, data classifications, and failure behavior are agreed.",
    ),
    (
        "Who will operate it after the pilot?",
        "A production owner, infrastructure owner, security contact, support route, alert route, and change process must be named. The current repository includes deployment and operations runbooks, but people and accountability complete the control.",
    ),
]
qa_close = Table(
    [
        [qa(*remaining_qa[0]), qa(*remaining_qa[1])],
        [qa(*remaining_qa[2]), qa(*remaining_qa[3])],
    ],
    colWidths=[89 * mm, 89 * mm],
)
qa_close.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]
    )
)
story.extend([qa_close, Spacer(1, 5 * mm)])
pilot = [
    ["Pilot decision", "Recommended scope", "Success evidence"],
    [
        "One program",
        "Fictional or anonymized data; defined roles; 4-8 week time box; no production integration dependency",
        "Users complete assigned workflows; approval trace is clear; leadership report is trusted; Arabic UAT issues are recorded and resolved",
    ],
    [
        "Technical gates",
        "Approved hosting region; security review; backup and restore exercise; monitoring owner; dependency scan; load-test target",
        "Signed gate checklist with evidence and named owners",
    ],
    [
        "Go / no-go review",
        "CTO, security, operations, product owner, and Arabic business reviewer",
        "A documented decision on production, remediation, or further pilot work",
    ],
]
story.extend(
    [
        table(pilot, [38 * mm, 70 * mm, 68 * mm]),
        Spacer(1, 6 * mm),
        callout(
            "Close with this",
            '"I am asking for permission to run a controlled pilot, not permission to bypass production governance. The product is ready to demonstrate; the pilot will generate the technical and operational evidence needed for a responsible production decision."',
        ),
        PageBreak(),
    ]
)
story.extend(
    [
        *title("Presenter runbook", "Your 15-minute briefing and meeting checklist"),
        p("Fifteen-minute sequence", "H2Brand"),
        bullet("0:00-1:00 - State the delivery problem and the one-sentence value."),
        bullet(
            "1:00-3:00 - Explain program, projects, tasks, shared workers, and the fictional KAU/KSU/KKU scenario."
        ),
        bullet(
            "3:00-5:30 - Cover team execution, two-stage completion approval, courses, trainees, sessions, and attendance."
        ),
        bullet(
            "5:30-8:00 - Show dashboards, reports, notifications, audit, Arabic output, and Hijri/Gregorian dates."
        ),
        bullet(
            "8:00-11:00 - Explain the cited AI briefing, fixed CEO Telegram channel, and governed recovery agent."
        ),
        bullet(
            "11:00-14:00 - Demonstrate Dashboard, KAU project, approval, recovery-agent checkpoint, report, and audit evidence."
        ),
        bullet(
            "14:00-15:00 - State the verified test evidence, name the honest production gates, and request the controlled pilot."
        ),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "Before the meeting",
                    "Start Docker, PostgreSQL, Redis, the web app, worker, and scheduler. Select Arabic and preload Dashboard, KAU project, Approval, Agent, Reports, and Audit tabs.",
                ),
                (
                    "If the live demo fails",
                    "Continue with the HTML screenshots. Do not troubleshoot infrastructure during the decision meeting; offer a technical follow-up session.",
                ),
                (
                    "Avoid overpromising",
                    'Say "implemented locally" for features and "required production gate" for SSO, hosting approval, load tests, penetration testing, restore evidence, and live-data approval.',
                ),
                (
                    "Meeting outcome",
                    "Ask for a named pilot sponsor, one program, fictional/anonymized data, 4-8 weeks, agreed success measures, and a technical/security review date.",
                ),
            ]
        ),
        Spacer(1, 6 * mm),
        callout(
            "Your strongest answer",
            '"The product is ready for a controlled pilot, and the remaining risks are visible, testable, and assigned to explicit production gates."',
        ),
        Spacer(1, 6 * mm),
        p("Evidence and repository references", "H2Brand"),
        p(
            "Repository sources: docs/SCOPE.md; BUSINESS_RULES.md; USER_ROLES.md; WORKFLOWS.md; ACCEPTANCE_CRITERIA.md; LOCALIZATION.md; SECURITY.md; TEST_STRATEGY.md; DEPLOYMENT.md; OPERATIONS.md; PHASE_13_VERIFICATION.md through PHASE_17_VERIFICATION.md.",
            "BodySmall",
        ),
    ]
)


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Insight Tracker Complete CTO Guide",
        author="Insight Tracker",
        subject="Complete features, AI governance, CTO questions, test evidence, 15-minute script, and pilot recommendation",
    )
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


if __name__ == "__main__":
    build()
