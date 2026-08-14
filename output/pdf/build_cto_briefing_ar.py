# ruff: noqa: E501
"""Build the complete Arabic RTL CTO preparation guide."""

from __future__ import annotations

from pathlib import Path

import build_cto_briefing as shared
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "insight-tracker-complete-cto-guide-ar.pdf"
LOGO = ROOT / "static" / "img" / "insight-tracker-logo.png"
MARK = ROOT / "static" / "img" / "insight-tracker-mark.png"
FONT = (
    ROOT / "static" / "vendor" / "fonts" / "NotoSansArabic-VariableFont_wdth,wght.ttf"
)
ASSETS = ROOT / "output" / "presentation" / "assets"

DEEP = shared.DEEP
FOREST = shared.FOREST
STONE = shared.STONE
PAPER = shared.PAPER
INK = shared.INK
MUTED = shared.MUTED
LINE = shared.LINE
WHITE = colors.white

pdfmetrics.registerFont(TTFont("NotoArabicGuide", str(FONT)))

styles = getSampleStyleSheet()
for name, size, leading, color, _bold in [
    ("CoverKickerAr", 10, 14, colors.HexColor("#DCE1D2"), False),
    ("CoverTitleAr", 31, 39, WHITE, True),
    ("CoverLeadAr", 13, 20, colors.HexColor("#E6E9DF"), False),
    ("KickerAr", 9, 13, FOREST, True),
    ("H1Ar", 22, 29, DEEP, True),
    ("H2Ar", 13.5, 20, DEEP, True),
    ("BodyAr", 9.3, 15.2, INK, False),
    ("SmallAr", 8.1, 12.8, MUTED, False),
    ("BulletAr", 8.9, 14.4, INK, False),
    ("CalloutTitleAr", 13.5, 20, WHITE, True),
    ("CalloutBodyAr", 9.3, 15.2, colors.HexColor("#EDF0E8"), False),
    ("TableHeadAr", 7.7, 11.5, WHITE, True),
    ("TableCellAr", 7.5, 11.4, INK, False),
    ("QAr", 9.1, 13.6, DEEP, True),
    ("AAr", 8.1, 12.4, INK, False),
]:
    styles.add(
        ParagraphStyle(
            name,
            fontName="NotoArabicGuide",
            fontSize=size,
            leading=leading,
            textColor=color,
            alignment=TA_RIGHT,
            spaceAfter=4 if "Cover" not in name else 10,
        )
    )


def ar(text: str) -> str:
    return shared.rtl(text)


def p(text: str, style: str = "BodyAr") -> Paragraph:
    return Paragraph(ar(text), styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(ar(f"• {text}"), styles["BulletAr"])


def title(kicker: str, heading: str, lead: str | None = None) -> list:
    items = [p(kicker, "KickerAr"), p(heading, "H1Ar")]
    if lead:
        items.append(p(lead, "BodyAr"))
    items.extend([Spacer(1, 2 * mm), shared.Rule(180 * mm), Spacer(1, 4 * mm)])
    return items


def callout(heading: str, text: str, width: float = 180 * mm) -> Table:
    result = Table(
        [[[p(heading, "CalloutTitleAr"), p(text, "CalloutBodyAr")]]], colWidths=[width]
    )
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DEEP),
                ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
            ]
        )
    )
    return result


def table(data: list[list[str]], widths: list[float]) -> Table:
    converted = []
    for row_index, row in enumerate(data):
        style = "TableHeadAr" if row_index == 0 else "TableCellAr"
        converted.append([p(cell, style) for cell in reversed(row)])
    result = Table(
        converted, colWidths=list(reversed(widths)), repeatRows=1, hAlign="RIGHT"
    )
    result.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), DEEP),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [WHITE, colors.HexColor("#F7F6F0")],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )
    return result


def cards(items: list[tuple[str, str]], columns: int = 2) -> Table:
    cells = [[p(heading, "H2Ar"), p(text, "SmallAr")] for heading, text in items]
    rows = [cells[index : index + columns] for index in range(0, len(cells), columns)]
    if rows and len(rows[-1]) < columns:
        rows[-1].extend([[] for _ in range(columns - len(rows[-1]))])
    rows = [list(reversed(row)) for row in rows]
    width = 176 * mm / columns
    result = Table(rows, colWidths=[width] * columns, hAlign="RIGHT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF6")),
                ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.55, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
            ]
        )
    )
    return result


def screenshot(path: Path, width: float, caption: str) -> Table:
    with PILImage.open(path) as source:
        ratio = source.height / source.width
    image = Image(str(path), width=width, height=width * ratio)
    frame = Table([[image], [p(caption, "SmallAr")]], colWidths=[width + 4 * mm])
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


def qa(question: str, answer: str) -> Table:
    result = Table([[p(question, "QAr")], [p(answer, "AAr")]], colWidths=[85 * mm])
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF6")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return result


def qa_grid(items: list[tuple[str, str]]) -> Table:
    rows = []
    for index in range(0, len(items), 2):
        pair = [qa(*items[index])]
        if index + 1 < len(items):
            pair.insert(0, qa(*items[index + 1]))
        rows.append(pair)
    result = Table(rows, colWidths=[89 * mm, 89 * mm], hAlign="RIGHT")
    result.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    return result


def draw_contained(
    canvas: Canvas, path: Path, x: float, y: float, width: float, height: float
) -> None:
    shared.draw_contained(canvas, path, x, y, width, height)


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
        canvas.line(18 * mm, 18 * mm, page_width - 18 * mm, 18 * mm)
        canvas.setFillColor(colors.HexColor("#DCE1D2"))
        canvas.setFont("NotoArabicGuide", 8)
        canvas.drawRightString(
            page_width - 18 * mm,
            10.8 * mm,
            ar("إنسايت تراكر - موجز داخلي لمدير التقنية - 4 أغسطس 2026"),
        )
    else:
        canvas.setFillColor(DEEP)
        canvas.rect(0, page_height - 7 * mm, page_width, 7 * mm, fill=1, stroke=0)
        draw_contained(canvas, MARK, 16 * mm, page_height - 18 * mm, 13 * mm, 8 * mm)
        canvas.setFillColor(DEEP)
        canvas.setFont("NotoArabicGuide", 8.5)
        canvas.drawRightString(
            page_width - 18 * mm, page_height - 14.8 * mm, ar("إنسايت تراكر")
        )
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 14 * mm, page_width - 18 * mm, 14 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("NotoArabicGuide", 7.8)
        canvas.drawRightString(
            page_width - 18 * mm, 8 * mm, ar("مناقشة تجربة داخلية مع مدير التقنية")
        )
        canvas.drawString(18 * mm, 8 * mm, f"{doc.page}")
    canvas.restoreState()


story = []

# 1 - الغلاف
story.extend(
    [
        Spacer(1, 82 * mm),
        p("موجز داخلي لمدة 15 دقيقة لمدير التقنية", "CoverKickerAr"),
        p("إنسايت تراكر", "CoverTitleAr"),
        p("منظومة عربية آمنة من خطة البرنامج إلى النتيجة المتحقق منها.", "CoverLeadAr"),
        Spacer(1, 12 * mm),
        p(
            "دليل شامل للخصائص، وحوكمة الذكاء الاصطناعي، والوضع التقني، والأسئلة المتوقعة، وأدلة الاختبار، ونص العرض، وتوصية التجربة.",
            "CoverLeadAr",
        ),
        Spacer(1, 8 * mm),
        callout(
            "القرار الموصى به",
            "اعتماد تجربة محكومة لبرنامج واحد باستخدام بيانات خيالية أو مجهولة. ويبقى الإنتاج مشروطاً باعتماد الأمن وإقامة البيانات وملكية التشغيل واختبار الاستعادة.",
            118 * mm,
        ),
        PageBreak(),
    ]
)

# 2 - النظرة التنفيذية
story.extend(title("النظرة التنفيذية", "ما المنتج؟ ولماذا تستخدمه الجامعة؟"))
overview = [
    p(
        "إنسايت تراكر تطبيق مبني بـ Django وPostgreSQL يجمع البرامج والمشاريع والدورات والمهام والأشخاص والحضور والموافقات والأدلة والإشعارات واللوحات والتقارير في مساحة واحدة مضبوطة بالصلاحيات."
    ),
    bullet(
        "ترى القيادة التقدم الحالي والعمل المتأخر وحالة الموافقات دون انتظار تقارير يدوية."
    ),
    bullet("تعمل الفرق ضمن تسلسل واضح ومسؤوليات محددة وسجل نشاط دائم."),
    bullet("العربية لغة واجهة وتقارير أساسية، والإنجليزية متاحة مع RTL/LTR صحيح."),
    bullet("تُؤرشف السجلات المهمة بدلاً من حذفها بصمت."),
]
row = Table(
    [
        [
            screenshot(
                ASSETS / "dashboard-ar.png",
                83 * mm,
                "لوحة عربية حقيقية للبيانات التجريبية.",
            ),
            overview,
        ]
    ],
    colWidths=[90 * mm, 86 * mm],
    hAlign="RIGHT",
)
row.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]
    )
)
story.extend(
    [
        row,
        Spacer(1, 5 * mm),
        callout(
            "الإجابة في جملة",
            "منصة داخلية لضبط التنفيذ تربط الخطة بالأشخاص والموافقات والأدلة بالعربية والإنجليزية.",
        ),
        PageBreak(),
    ]
)

# 3 - السيناريو
story.extend(
    title(
        "سيناريو جامعي خيالي", "كيف تترابط البرامج والمشاريع والمهام والموارد المشتركة؟"
    )
)
story.extend(
    [
        table(
            [
                ["البرنامج", "مشاريع مثال", "نموذج الأشخاص"],
                [
                    "الخدمات الرقمية في KAU",
                    "بوابة الخدمات الطلابية الذكية؛ منصة التحليلات الأكاديمية",
                    "متخصصون في KAU مع منسق ومحلل مشتركين",
                ],
                [
                    "تمكين البحث في KSU",
                    "حاضنة الابتكار البحثي؛ منصة إدارة المختبرات",
                    "متخصصون في KSU مع الموارد المشتركة نفسها",
                ],
                [
                    "تجربة الطالب في KKU",
                    "تطبيق رحلة الطالب؛ مركز الدعم الرقمي",
                    "متخصصون في KKU وأدوار مشتركة حيث يُسمح",
                ],
            ],
            [40 * mm, 72 * mm, 64 * mm],
        ),
        Spacer(1, 4 * mm),
        p(
            "البيانات خيالية ومصممة لإثبات تكرار نمط المهمة عبر المشاريع مع بقاء العمل والعضوية الخاصة بكل مشروع منفصلة."
        ),
        screenshot(
            ASSETS / "projects-ar.png",
            165 * mm,
            "سجل المشاريع العربي ويعرض مشاريع KAU وKSU وKKU الخيالية.",
        ),
        Spacer(1, 2 * mm),
        callout(
            "ما الذي تعرضه؟",
            "افتح سجل المشاريع ثم مشروع بوابة الخدمات الطلابية الذكية في KAU، وأشر إلى الاسم والعميل والتصنيف والمدير والمشرف والأولوية والفريق والتقدم والميزانية والتواريخ والموافقة.",
        ),
        PageBreak(),
    ]
)

# 4 - سير العمل والأدوار
story.extend(title("سير التشغيل", "ما الذي يختبره كل عضو في الفريق؟"))
story.extend(
    [
        table(
            [
                ["الخطوة", "الفاعل", "سلوك النظام"],
                [
                    "1. التخطيط",
                    "المدير التنفيذي / مدير المشروع",
                    "إنشاء المشروع والفريق والمهام والمراحل والتواريخ والأولويات والمسؤوليات.",
                ],
                [
                    "2. التنفيذ",
                    "الموظف / المتعاقد",
                    "تحديث العمل المسند والتقدم والتعليقات والعلامات والأدلة المسموحة.",
                ],
                [
                    "3. المراجعة",
                    "المشرف",
                    "مراجعة المرحلة الأولى وقبولها أو رفضها بسبب مسجل.",
                ],
                [
                    "4. الاعتماد",
                    "مدير المشروع",
                    "قرار ثانٍ مستقل، ولا ينفذ الشخص نفسه المرحلتين.",
                ],
                [
                    "5. الحوكمة",
                    "الأدوار المخولة",
                    "عرض اللوحة والعمل المتأخر والتدقيق وتقارير PDF/XLSX المقيدة.",
                ],
            ],
            [22 * mm, 40 * mm, 114 * mm],
        ),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "المسؤول التقني",
                    "يدير الإعداد والحسابات ولا يتجاوز صلاحيات الكائنات.",
                ),
                ("المدير التنفيذي", "رؤية على مستوى المحفظة وفق النطاق الممنوح."),
                (
                    "مدير المشروع والمشرف",
                    "يمتلكان التنفيذ ويؤديان مرحلتي الاعتماد المستقلتين.",
                ),
                ("الموظف والمتعاقد", "يعملان داخل المشاريع والمهام المسندة فقط."),
                ("المدرب الخارجي", "يستخدم رابط حضور عشوائياً مؤقتاً لجلسة واحدة."),
                (
                    "العمل المتزامن",
                    "تعمل أجهزة وجلسات متعددة مع حماية المعاملات والقيود للكتابات الحرجة.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "قاعدة يجب تذكرها",
            "المشرف أولاً ثم مدير المشروع. لا يجمع شخص واحد المرحلتين. الرفض يتطلب سبباً، وإعادة التقديم محفوظة، والتاريخ لا يُعاد كتابته.",
        ),
        PageBreak(),
    ]
)

# 5 - القدرات
story.extend(title("قدرات المنتج", "الخصائص المنفذة بالفعل"))
story.extend(
    [
        cards(
            [
                (
                    "إدارة البرامج",
                    "مشاريع وأقسام وعملاء وتصنيفات ودورات ومهام ومراحل وفرق وتقدم وأرشيف وKanban وتقويم وخط زمني وGantt.",
                ),
                (
                    "الأشخاص والحضور",
                    "مستخدمون ومتدربون واستيراد وجلسات وروابط مدرب وإرسال ومراجعة وتصحيح وتقارير حضور مجمعة.",
                ),
                (
                    "الحوكمة",
                    "موافقات متسلسلة وتدقيق تراكمي وبحث مقيد وإشعارات وأرشفة واستعادة.",
                ),
                (
                    "التقارير",
                    "تقدم المشروع والمهام المتأخرة والحضور بصيغ PDF/XLSX وبالعربية أو الإنجليزية والتاريخين الهجري والميلادي.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
    ]
)
screens = Table(
    [
        [
            screenshot(ASSETS / "reports-ar.png", 84 * mm, "مركز التقارير العربي."),
            screenshot(
                ASSETS / "project-detail-ar.png",
                84 * mm,
                "تفاصيل مشروع KAU وضوابط الفريق.",
            ),
        ]
    ],
    colWidths=[88 * mm, 88 * mm],
)
screens.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ]
    )
)
story.extend(
    [
        screens,
        Spacer(1, 3 * mm),
        p(
            "ضوابط التصدير: 5,000 صف كحد أقصى، وفترة لا تتجاوز 366 يوماً، وحضور مجمع، وصفوف مقيدة بالصلاحيات، وتحييد صيغ الجداول، ولا روابط دائمة للملف المولد.",
            "SmallAr",
        ),
        PageBreak(),
    ]
)

# 6 - المرحلة 15
story.extend(title("المرحلة 15 - موجز المشروع الذكي", "تلخيص موثق دون أي إجراء ذاتي"))
story.extend(
    [
        cards(
            [
                (
                    "ما الذي يفعله؟",
                    "يبني أدلة محدودة من حالة المشروع والتقدم والمهام والمراحل والموافقات والنشاط الحديث، ثم يعيد ملخصاً ومخاطر وتوصيات وفجوات بيانات.",
                ),
                (
                    "ما الذي لا يفعله؟",
                    "لا أدوات ولا كتابة ولا أوامر نظام ولا SQL ولا ملفات ولا روابط عشوائية ولا موافقات ولا تغيير للمهام.",
                ),
                (
                    "من يراه؟",
                    "المدير التنفيذي والمدير التنفيذي المساعد ومدير المشروع والمشرف، فقط ضمن رؤية المشروع الحالية.",
                ),
                (
                    "الكفاءة",
                    "Groq عبر openai/gpt-oss-120b افتراضياً، مع حدود أدلة ورموز وطلبات وبصمات ومقاييس تخزين مؤقت وخيار 20B الصريح.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        screenshot(
            ASSETS / "ai-briefing-ar.png",
            162 * mm,
            "موجز عربي حتمي للاختبار مع استشهادات قابلة للفتح.",
        ),
        Spacer(1, 3 * mm),
        callout(
            "حد الثقة",
            "كل حقيقة تحتاج مرجعاً داخلياً مسموحاً، وأي استشهاد مجهول أو غير مصرح به يرفض المخرج. ويظل الناتج مسودة مولدة بالذكاء الاصطناعي تحتاج مراجعة بشرية.",
        ),
        PageBreak(),
    ]
)

# 7 - المرحلة 16
story.extend(
    title("المرحلة 16 - قناة المدير التنفيذي", "تقارير عربية ثابتة عبر تيليجرام وn8n")
)
story.extend(
    [
        table(
            [
                ["الخطوة", "التحكم"],
                ["أمر ثابت", "المساعدة أو المهام الحالية أو المتأخرة أو الحضور فقط."],
                [
                    "تحقق n8n",
                    "محادثة المدير المحددة وطابع زمني وتوقيع HMAC ورمز استخدام واحد.",
                ],
                ["تفويض Django", "هوية ودور وصلاحية وحدود ونطاق تقرير."],
                [
                    "إنشاء",
                    "ملخص عربي أو PDF بعلامة إنسايت تراكر وتاريخ هجري وميلادي.",
                ],
                [
                    "تسليم",
                    "رابط لمرة واحدة لمدة عشر دقائق، وتدقيق، ومنع تكرار التنبيه الحرج.",
                ],
            ],
            [45 * mm, 131 * mm],
        ),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "خصوصية الحضور",
                    "قد يحتوي PDF المرسل إلى محادثة المدير المربوطة أسماء المتدربين وحالات الحضور المعتمدة فقط؛ لا هاتف أو بريد أو ملاحظات أو ملفات.",
                ),
                (
                    "حد Groq",
                    "يستقبل المجاميع فقط ولا يستقبل أسماء المتدربين أو بيانات الاتصال أو ملاحظات الحضور.",
                ),
                (
                    "حد n8n",
                    "لا يملك بيانات دخول لقاعدة البيانات ولا واجهة كتابة أعمال عامة.",
                ),
                (
                    "التفعيل",
                    "المسار غير نشط حتى اعتماد روبوت وأسرار وتكوين HTTPS واختبار قبول خصوصية في بيئة الاختبار.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "لماذا هو آمن؟",
            "القناة ليست محادثة حرة. الأوامر والمستلم والبيانات والتوقيع والانتهاء محددة، ويظل Django مصدر التفويض والبيانات.",
        ),
        PageBreak(),
    ]
)

# 8 - المرحلة 17
story.extend(
    title("المرحلة 17 - وكيل تعافي المشروع", "يخطط ويلاحظ ويقترح وينتظر وينفذ ثم يتحقق")
)
story.extend(
    [
        table(
            [
                ["الحالة", "ما يحدث"],
                ["التخطيط", "هدف محدد مسبقاً وخطة متعددة الخطوات وحد أقصى ثماني خطوات."],
                [
                    "الملاحظة",
                    "اختيار ديناميكي لأداتين قراءة على الأقل، وتؤثر النتيجة في الخطوة التالية.",
                ],
                ["الاقتراح", "قيم قبلية ومقترحة موثقة، دون تغيير بيانات الأعمال."],
                ["الموافقة", "توقف إلزامي لقرار بشري مسبب."],
                [
                    "التنفيذ",
                    "إعادة فحص الصلاحية والنطاق والانتهاء وبصمة الحالة، ثم تنفيذ معاملاتي مرة واحدة.",
                ],
                [
                    "التحقق",
                    "قراءة الحالة الفعلية بعد الإجراء وإنشاء خلاصة نهائية موثقة.",
                ],
            ],
            [42 * mm, 134 * mm],
        ),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "ذاكرة مراجعة",
                    "لا تدخل الذاكرة إلا خلاصة تشغيل مكتمل راجعه إنسان، وتُستخدم لاحقاً في المشروع نفسه مع الاستشهاد.",
                ),
                (
                    "أفعال مقترحة فقط",
                    "تحديث مهمة أو إسناد أو تعليق أو موعد أو إشعار فريق؛ ولا يوجد تجاوز لاعتماد الإكمال.",
                ),
                (
                    "تنفيذ آمن",
                    "مفتاح عدم تكرار ومعاملة وقفل وإعادة تحقق من الحالة والصلاحيات ثم تحقق نهائي.",
                ),
                (
                    "رفض آمن",
                    "المحاولات الخبيثة أو المزورة أو غير المصرح بها أو المتقادمة أو المتكررة أو المتجاوزة للميزانية تفشل مغلقة.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "الجملة الأهم",
            "النموذج لا يكتب في بيانات الأعمال. الإنسان يوافق، ثم يقرر الخادم إن كان الإجراء ما زال مسموحاً وآمناً للتنفيذ.",
        ),
        PageBreak(),
    ]
)

# 9 - البنية
story.extend(title("البنية التقنية", "تطبيق أحادي واضح وقابل للنشر"))
story.extend(
    [
        table(
            [
                ["الطبقة", "التقنية", "القيمة"],
                [
                    "الويب",
                    "Django 5.2 LTS، Python 3.13، Templates، Bootstrap 5، HTMX",
                    "واجهة خادم مترجمة ومسارات أعمال مركزية.",
                ],
                ["البيانات", "PostgreSQL", "معاملات وقيود وفهارس ومصدر حقيقة واحد."],
                [
                    "الخلفية",
                    "Celery وRedis",
                    "إشعارات وتقارير ذكاء اصطناعي ووكلاء وإعادة محاولة وصيانة.",
                ],
                ["التشغيل", "Docker وGunicorn", "بناء متكرر وهدف استضافة قابل للنقل."],
                [
                    "الملفات",
                    "تخزين خاص محلياً وS3 متوافق خاص في الإنتاج",
                    "أدلة غير عامة وتسليم مضبوط.",
                ],
                [
                    "المراقبة",
                    "سجلات منظمة ومعرف طلب وفحوص صحة وتدقيق",
                    "تشخيص دون كشف أسرار أو آثار خطأ للمستخدم.",
                ],
            ],
            [34 * mm, 70 * mm, 72 * mm],
        ),
        Spacer(1, 6 * mm),
        cards(
            [
                (
                    "موقف النشر",
                    "Render موثق كهدف، لكن الجامعة تعتمد المزود والمنطقة والخطة والنطاق والشبكة وإقامة البيانات.",
                ),
                (
                    "التوسع",
                    "يمكن تكرار طبقة الويب وتوسيع قاعدة البيانات والعمال، لكن سعة الجامعة تحتاج اختبار حمل واقعي.",
                ),
                (
                    "التكامل",
                    "الإصدار الحالي تطبيق أحادي، ويجب تحديد SSO والأنظمة المؤسسية وواجهات التكامل بعد التجربة.",
                ),
                (
                    "الصيانة",
                    "تطبيقات مجال وخدمات وترحيلات وواجهات typed واختبارات تجعل مخاطر التغيير مفهومة.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "إجابة معمارية صادقة",
            "البنية جاهزة لتجربة محكومة، أما طوبولوجيا الإنتاج والتكاملات فتُحسم مع فرق البنية والأمن في الجامعة.",
        ),
        PageBreak(),
    ]
)

# 10 - الأمن والعربية
story.extend(
    title("الأمن والخصوصية والعربية", "ضوابط موجودة وبوابات مطلوبة قبل الإطلاق")
)
story.extend(
    [
        cards(
            [
                (
                    "التحكم في الوصول",
                    "جلسات موثقة وحساب نشط وصلاحية دور وكائن وفحوص طريقة وCSRF وتصدير مقيد.",
                ),
                (
                    "المسارات الحساسة",
                    "معاملات للاستيراد والموافقات وتاريخ ثابت وروابط مدرب عشوائية مؤقتة ورموز مجزأة وفحص إعادة التشغيل.",
                ),
                (
                    "حماية البيانات",
                    "تحقق حجم وامتداد وMIME وملفات إنتاج خاصة وDEBUG مغلق وأسرار من البيئة ولا تصدير لتدقيق خام حساس.",
                ),
                (
                    "جودة العربية",
                    "يحفظ النص العربي دون تطبيع مدمر، مع بحث مراجع وRTL/LTR ومحتوى مختلط وPDF/XLSX وتاريخ هجري وميلادي.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
    ]
)
audit = Table(
    [
        [
            screenshot(
                ASSETS / "audit-ar.png",
                87 * mm,
                "عرض تدقيق عربي تراكمي ومقيد بالصلاحيات.",
            ),
            [
                p("الأهداف التشغيلية", "H2Ar"),
                bullet("هدف RPO: 24 ساعة، وRTO: 8 ساعات."),
                bullet("احتفاظ نسخة مشفرة: 35 يوماً."),
                bullet("اختبار استعادة معزول كل ربع سنة."),
                bullet("احتفاظ غير محدد المدة بسجلات التطبيق في الإصدار الأول."),
                Spacer(1, 2 * mm),
                p("ما لم ندّعه", "H2Ar"),
                bullet("لم تُنشأ أو تُستعد نسخة إنتاج حقيقية."),
                bullet("لم يُعتمد بعد مزود أو منطقة أو إقامة بيانات للإنتاج."),
                bullet("تعيين مالكي التشغيل ومسارات التنبيه بوابة إطلاق."),
            ],
        ]
    ],
    colWidths=[92 * mm, 84 * mm],
)
audit.setStyle(
    TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ]
    )
)
story.extend([audit, PageBreak()])

# 11 - الاختبارات
story.extend(title("أدلة التحقق", "ما الذي اختُبر ونجح، وما الذي لم ندّعه؟"))
story.extend(
    [
        table(
            [
                ["الدليل", "النتيجة", "التغطية"],
                [
                    "غير المتصفح",
                    "200 ناجح",
                    "نماذج وقيود ومحددات ونماذج إدخال وصلاحيات وخدمات ومعاملات وتقارير وذكاء اصطناعي وأمن واستيراد وتكاملات.",
                ],
                [
                    "Playwright",
                    "16 ناجح",
                    "مسارات عربية RTL وإنجليزية LTR وصلاحيات وتقارير وذكاء اصطناعي وجوال في Chrome.",
                ],
                ["الإجمالي", "216 ناجح", "آخر بوابة محلية كاملة في 2026-08-04."],
                [
                    "الجودة الساكنة",
                    "ناجح",
                    "Ruff وmypy عبر 281 ملفاً وفحوص Django وعدم انحراف الترحيلات وفرق Git.",
                ],
                [
                    "التوطين",
                    "ناجح",
                    "1,173 رسالة عربية و0 غير مترجمة، ودوران Unicode وRTL/LTR والتاريخان.",
                ],
                [
                    "الفحص البصري",
                    "ناجح",
                    "تصيير PDF والعرض وفحص تقارير PDF وExcel بالعربية والإنجليزية.",
                ],
            ],
            [38 * mm, 36 * mm, 102 * mm],
        ),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "اختبارات الوحدات",
                    "القواعد والمعادلات والمتحققات والحدود والأرشفة وإعادة المحاولة.",
                ),
                (
                    "اختبارات التكامل",
                    "واجهات Django وPostgreSQL والصلاحيات والاستيراد وسياسات التقارير وعدد الاستعلامات.",
                ),
                (
                    "اختبارات المتصفح",
                    "رحلات مستخدم فعلية بالعربية والإنجليزية وأحجام شاشة ممثلة.",
                ),
                (
                    "اختبارات الأمن",
                    "الوصول الخاطئ وحقن التعليمات والمعرفات المزورة وتقادم الحالة وإعادة HMAC والتكرار والرفع والروابط المؤقتة والسجلات الحساسة.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "لا تبالغ في الادعاء",
            "لا يزال اختبار اختراق رسمي وحمل بحجم الجامعة واستعادة كوارث ومراجعة مزود وفحص ثغرات الإصدار واختبار قبول إنتاجي مطلوبة قبل الإطلاق.",
        ),
        PageBreak(),
    ]
)

# 12 - أسئلة الذكاء الاصطناعي
story.extend(
    title(
        "أسئلة مدير التقنية عن الذكاء الاصطناعي",
        "إجابات مختصرة عن الموجز وتيليجرام ووكيل التعافي",
    )
)
story.extend(
    [
        qa_grid(
            [
                (
                    "لماذا نستخدم LLM؟",
                    "لدوره في التلخيص والتخطيط عبر أدلة مصرح بها؛ أما الحساب والصلاحيات والتنفيذ والتحقق فتظل خدمات حتمية.",
                ),
                (
                    "هل يغير السجلات وحده؟",
                    "لا. المرحلة 15 قراءة فقط، والمرحلة 17 تقترح وتنتظر الإنسان ثم يعيد Django فحص الصلاحية والحالة قبل تنفيذ واحد.",
                ),
                (
                    "كيف نمنع الهلوسة؟",
                    "مخطط صارم واستشهاد إلزامي ورفض للمراجع المجهولة ورسالة واضحة بأن المخرج يحتاج مراجعة.",
                ),
                (
                    "ما الذي يصل إلى Groq؟",
                    "أدلة محدودة ومقيدة لازمة للهدف؛ لا أسرار أو ملفات أو تدقيق خام أو اتصال متدربين أو ملاحظات حضور.",
                ),
                (
                    "كيف نضبط الرموز؟",
                    "حدود للسجلات والنتائج والخطوات والرموز والوقت والطلبات مع بصمات ومقاييس تخزين مؤقت وخيار 20B الصريح.",
                ),
                (
                    "هل يفتح حقن التعليمات أدوات؟",
                    "لا. النص غير موثوق، والأدوات والمعاملات تمر بمخططات ونطاق مشروع؛ shell وSQL والويب والأسرار غير موجودة.",
                ),
                (
                    "لماذا n8n آمن؟",
                    "لا قاعدة بيانات ولا كتابة أعمال، مع HMAC وطابع زمني ورمز لمرة واحدة وربط دقيق بمحادثة المدير.",
                ),
                (
                    "ما المطلوب للتفعيل الحي؟",
                    "إدارة أسرار وموقف معالجة وإقامة بيانات واختبار أمني وخصوصية في staging وملكية مراقبة وقرار إنتاج صريح.",
                ),
            ]
        ),
        PageBreak(),
    ]
)

# 13 - أسئلة عامة
story.extend(title("أسئلة مدير التقنية العامة", "إجابات جاهزة للاجتماع"))
story.extend(
    [
        qa_grid(
            [
                (
                    "لماذا لا نستخدم Jira أو Asana؟",
                    "لأن النظام يجمع تنفيذ المشاريع والدورات والحضور وموافقتين والتقارير العربية ووصول الجامعة في نموذج واحد. تثبت التجربة أين تضيف هذه الوحدة قيمة.",
                ),
                (
                    "أين ستستضاف البيانات؟",
                    "التطبيق قابل للنقل، لكن المزود والمنطقة السعودية والشبكة وإقامة البيانات قرارات صريحة قبل استخدام بيانات حقيقية.",
                ),
                (
                    "هل يدعم SSO؟",
                    "الإصدار الحالي يستخدم حسابات Django داخلية آمنة. لا ندعي اكتمال SSO؛ ويمكن تحديد SAML/OIDC بعد معرفة مزود الجامعة وقواعد الأدوار وMFA.",
                ),
                (
                    "هل يعمل مستخدمون كثيرون معاً؟",
                    "نعم عبر أجهزة وجلسات منفصلة مع معاملات وقيود PostgreSQL، لكن السعة الدقيقة تحتاج اختبار حمل واقعي.",
                ),
                (
                    "كيف تمنعون رؤية برنامج آخر؟",
                    "كل واجهة وتصدير يتحققان من الدور والكائن، وتختبر الروابط المباشرة ومحاولات النطاق الخاطئ.",
                ),
                (
                    "هل يمكن حذف التدقيق؟",
                    "السجلات المهمة تُؤرشف، وتاريخ الموافقات ثابت، والتدقيق تراكمي، والتصدير منقح.",
                ),
                (
                    "كيف تعمل النسخ الاحتياطية؟",
                    "الهدف RPO 24 ساعة وRTO 8 ساعات و35 يوماً مشفرة واختبار استعادة ربع سنوي، مع ضرورة دليل استعادة حقيقي قبل الإطلاق.",
                ),
                (
                    "هل العربية ترجمة عناوين فقط؟",
                    "لا. تشمل RTL والنص المحفوظ والبحث والمحتوى المختلط وPDF/XLSX والتاريخين الهجري والميلادي واختبارات المتصفح.",
                ),
            ]
        ),
        PageBreak(),
    ]
)

# 14 - القرار
story.extend(title("القرار والخطوات التالية", "كيف تُغلق الاجتماع؟"))
story.extend(
    [
        qa_grid(
            [
                (
                    "هل هو جاهز للإنتاج اليوم؟",
                    "الخصائص مكتملة ومتحقق منها محلياً، لكن البيانات الحية تحتاج اعتماد الاستضافة وإقامة البيانات وSSO والأسرار والتخزين وفحص الثغرات وUAT والمراقبة والاستعادة والحمل.",
                ),
                (
                    "ماذا عن الجوال؟",
                    "تطبيق ويب متجاوب اختُبر على أحجام ممثلة، وليس تطبيق iOS أو Android أصلياً.",
                ),
                (
                    "هل يتكامل مع أنظمة الجامعة؟",
                    "البنية تسمح بتكاملات محددة، لكن لا ينبغي وعد SIS أو HR أو LMS أو بريد أو SSO قبل اتفاق الواجهات والملكية والتصنيف والفشل.",
                ),
                (
                    "من سيشغله؟",
                    "يجب تعيين مالك إنتاج وبنية وأمن ودعم وتنبيه وتغيير؛ أدلة التشغيل موجودة، لكن الأشخاص والمساءلة يكملان الضبط.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        table(
            [
                ["قرار التجربة", "النطاق", "دليل النجاح"],
                [
                    "برنامج واحد",
                    "بيانات خيالية أو مجهولة؛ أدوار محددة؛ 4-8 أسابيع",
                    "إكمال المسارات ووضوح الموافقات وثقة التقرير ومعالجة ملاحظات العربية",
                ],
                [
                    "بوابات تقنية",
                    "منطقة معتمدة؛ أمن؛ استعادة؛ مراقبة؛ فحص تبعيات؛ هدف حمل",
                    "قائمة أدلة موقعة بمالكين محددين",
                ],
                [
                    "قرار الإطلاق",
                    "مدير التقنية والأمن والعمليات ومالك المنتج ومراجع العربية",
                    "قرار موثق بالإنتاج أو المعالجة أو تمديد التجربة",
                ],
            ],
            [38 * mm, 70 * mm, 68 * mm],
        ),
        Spacer(1, 5 * mm),
        callout(
            "اختم بهذه العبارة",
            "أطلب إذناً لتجربة محكومة، لا لتجاوز حوكمة الإنتاج. المنتج جاهز للعرض، وستنتج التجربة الأدلة التقنية والتشغيلية اللازمة لقرار إنتاج مسؤول.",
        ),
        PageBreak(),
    ]
)

# 15 - دليل المتحدث
story.extend(title("دليل المتحدث", "خطة العرض لمدة 15 دقيقة وقائمة الاجتماع"))
story.extend(
    [
        p("تسلسل الدقائق الخمس عشرة", "H2Ar"),
        bullet("0:00-1:00 - اشرح مشكلة التنفيذ والقيمة في جملة."),
        bullet(
            "1:00-3:00 - اشرح البرنامج والمشاريع والمهام والموارد المشتركة وسيناريو KAU/KSU/KKU."
        ),
        bullet(
            "3:00-5:30 - غطّ تنفيذ الفريق والموافقتين والدورات والمتدربين والجلسات والحضور."
        ),
        bullet(
            "5:30-8:00 - اعرض اللوحات والتقارير والإشعارات والتدقيق والعربية والتاريخين."
        ),
        bullet(
            "8:00-11:00 - اشرح الموجز الموثق وتيليجرام الثابت ووكيل التعافي المحكوم."
        ),
        bullet(
            "11:00-14:00 - اعرض اللوحة ومشروع KAU والموافقة ونقطة الوكيل والتقرير والتدقيق."
        ),
        bullet("14:00-15:00 - اذكر الاختبارات والبوابات الصادقة واطلب التجربة."),
        Spacer(1, 5 * mm),
        cards(
            [
                (
                    "قبل الاجتماع",
                    "شغل Docker وPostgreSQL وRedis والويب والعامل والمجدول، واختر العربية وجهز تبويبات اللوحة وKAU والموافقة والوكيل والتقارير والتدقيق.",
                ),
                (
                    "إذا فشل العرض الحي",
                    "تابع بلقطات HTML ولا تصلح البنية أثناء اجتماع القرار؛ اقترح جلسة تقنية لاحقة.",
                ),
                (
                    "تجنب المبالغة",
                    "قل «منفذ محلياً» للخصائص و«بوابة إنتاج مطلوبة» لـ SSO والاستضافة والحمل والاختراق والاستعادة والبيانات الحية.",
                ),
                (
                    "نتيجة الاجتماع",
                    "اطلب راعياً وبرنامجاً واحداً وبيانات خيالية و4-8 أسابيع ومقاييس نجاح وموعد مراجعة تقنية وأمنية.",
                ),
            ]
        ),
        Spacer(1, 5 * mm),
        callout(
            "أقوى إجابة لديك",
            "المنتج جاهز لتجربة محكومة، والمخاطر المتبقية مرئية وقابلة للاختبار ومربوطة ببوابات إنتاج صريحة.",
        ),
        Spacer(1, 5 * mm),
        p("مراجع الأدلة", "H2Ar"),
        p(
            "docs/SCOPE.md; BUSINESS_RULES.md; USER_ROLES.md; WORKFLOWS.md; ACCEPTANCE_CRITERIA.md; LOCALIZATION.md; SECURITY.md; TEST_STRATEGY.md; DEPLOYMENT.md; OPERATIONS.md; PHASE_13_VERIFICATION.md through PHASE_17_VERIFICATION.md.",
            "SmallAr",
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
        title="دليل إنسايت تراكر الكامل لمدير التقنية",
        author="إنسايت تراكر",
        subject="الخصائص الكاملة وحوكمة الذكاء الاصطناعي والأسئلة والاختبارات ونص العرض والتجربة",
    )
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


if __name__ == "__main__":
    build()
