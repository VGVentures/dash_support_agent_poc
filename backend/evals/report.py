"""Render evals/results.json as a PDF report.

run_evals.py and compare_models.py call this automatically now, so you only
need to run it by hand to rebuild the PDF from existing result files:
    python3 evals/report.py
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand palette
VGV_BLUE = colors.HexColor("#2A48DE")
VGV_NAVY = colors.HexColor("#0A1530")
VGV_BLACK = colors.HexColor("#232326")
VGV_WHITE = colors.HexColor("#FFFFFF")
VGV_BLUE_20 = colors.HexColor("#D5DDF8")
VGV_GRAY_DEEP = colors.HexColor("#838998")
VGV_GRAY = colors.HexColor("#D2D5DD")
PASS_COLOR = colors.HexColor("#00A644")  
FAIL_COLOR = colors.HexColor("#FC5D42")

EVALS_DIR = Path(__file__).resolve().parent
FONTS_DIR = EVALS_DIR / "fonts"


def register_fonts() -> str:
    """Register Poppins if bundled, otherwise fall back to Helvetica."""
    regular = FONTS_DIR / "Poppins-Regular.ttf"
    medium = FONTS_DIR / "Poppins-Medium.ttf"
    bold = FONTS_DIR / "Poppins-Bold.ttf"
    if not (regular.exists() and medium.exists() and bold.exists()):
        return "Helvetica"

    pdfmetrics.registerFont(TTFont("Poppins", str(regular)))
    pdfmetrics.registerFont(TTFont("Poppins-Medium", str(medium)))
    pdfmetrics.registerFont(TTFont("Poppins-Bold", str(bold)))
    pdfmetrics.registerFontFamily(
        "Poppins", normal="Poppins", bold="Poppins-Bold", boldItalic="Poppins-Bold"
    )
    return "Poppins"


def build_styles():
    base_font = register_fonts()
    bold_font = f"{base_font}-Bold" if base_font == "Poppins" else "Helvetica-Bold"
    medium_font = f"{base_font}-Medium" if base_font == "Poppins" else "Helvetica"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=bold_font,
            textColor=VGV_NAVY,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "Meta", parent=styles["Normal"], fontName=base_font, textColor=VGV_GRAY_DEEP, spaceAfter=16
        )
    )
    styles.add(
        ParagraphStyle(
            "CaseName",
            parent=styles["Heading2"],
            fontName=bold_font,
            textColor=VGV_NAVY,
            spaceBefore=14,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "Label",
            parent=styles["Normal"],
            fontName=medium_font,
            textColor=VGV_GRAY_DEEP,
            fontSize=9,
            spaceBefore=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body", parent=styles["Normal"], fontName=base_font, textColor=VGV_BLACK, spaceAfter=4
        )
    )
    return styles, base_font, bold_font


def add_comparison_section(
    story: list,
    styles,
    base_font: str,
    bold_font: str,
    csv_path: Path,
    plot_path: Path,
) -> None:
    """Append a "Model Comparison" section built from compare_models.py output.

    No-op if `csv_path` doesn't exist, so the report still builds fine when
    only a single-model eval run has been done.
    """
    if not csv_path.exists():
        return

    df = pd.read_csv(csv_path)
    summary = df.groupby("model").agg(
        pass_rate=("passed", "mean"),
        avg_duration_seconds=("duration_seconds", "mean"),
    )

    story.append(Paragraph("Model Comparison", styles["ReportTitle"]))
    story.append(
        Paragraph(f"{len(df['case'].unique())} cases × {len(summary)} models", styles["Meta"])
    )

    rows = [["Model", "Pass rate", "Avg duration"]]
    for model, row in summary.iterrows():
        rows.append([model, f"{row['pass_rate'] * 100:.0f}%", f"{row['avg_duration_seconds']:.2f}s"])

    table = Table(rows, colWidths=[3.3 * inch, 1.4 * inch, 1.4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, VGV_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), VGV_NAVY),
                ("TEXTCOLOR", (0, 1), (-1, -1), VGV_BLACK),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [VGV_WHITE, VGV_BLUE_20]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 16))

    if plot_path.exists():
        px_width, px_height = PILImage.open(plot_path).size
        draw_width = 6.5 * inch
        draw_height = draw_width * (px_height / px_width)
        story.append(Image(str(plot_path), width=draw_width, height=draw_height))


def heading_for(results: list[dict]) -> str:
    models = {r["model"] for r in results if r.get("model")}
    if len(models) == 1:
        return f"Agent Behavior Evals — {models.pop()}"
    return "Agent Behavior Evals"


def add_eval_section(
    story: list,
    styles,
    base_font: str,
    bold_font: str,
    heading: str,
    generated_at: str,
    results: list[dict],
) -> None:
    passed = sum(1 for r in results if r["passed"])

    story.append(Paragraph(heading, styles["ReportTitle"]))
    story.append(Paragraph(f"Generated {generated_at}", styles["Meta"]))

    summary_color = PASS_COLOR if passed == len(results) else FAIL_COLOR
    summary_style = ParagraphStyle(
        "Summary", parent=styles["Heading3"], fontName=bold_font, textColor=summary_color
    )
    story.append(Paragraph(f"{passed}/{len(results)} cases passed", summary_style))
    story.append(Spacer(1, 6))

    summary_rows = [["", "Case", "Duration"]]
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        summary_rows.append([mark, r["name"], f"{r['duration_seconds']}s"])

    table = Table(summary_rows, colWidths=[0.6 * inch, 4.6 * inch, 0.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, VGV_BLUE),
                ("TEXTCOLOR", (1, 0), (-1, 0), VGV_NAVY),
                ("TEXTCOLOR", (0, 1), (0, -1), VGV_WHITE),
                ("TEXTCOLOR", (1, 1), (-1, -1), VGV_BLACK),
                ("ROWBACKGROUNDS", (1, 1), (-1, -1), [VGV_WHITE, VGV_BLUE_20]),
            ]
        )
    )
    for i, r in enumerate(results, start=1):
        bg = PASS_COLOR if r["passed"] else FAIL_COLOR
        table.setStyle(TableStyle([("BACKGROUND", (0, i), (0, i), bg)]))
    story.append(table)
    story.append(PageBreak())

    for r in results:
        mark_color = PASS_COLOR if r["passed"] else FAIL_COLOR
        mark_style = ParagraphStyle(
            "Mark", parent=styles["CaseName"], fontName=bold_font, textColor=mark_color
        )
        story.append(Paragraph(f"{'PASS' if r['passed'] else 'FAIL'} — {r['name']}", mark_style))
        story.append(HRFlowable(width="100%", color=VGV_GRAY, thickness=0.5))

        story.append(Paragraph("Prompt", styles["Label"]))
        story.append(Paragraph(escape(r["prompt"]), styles["Body"]))

        story.append(Paragraph("Reply", styles["Label"]))
        story.append(Paragraph(escape(r["reply"]), styles["Body"]))

        tool_calls = ", ".join(r["tool_calls"]) or "(none)"
        story.append(Paragraph("Tool calls", styles["Label"]))
        story.append(Paragraph(escape(tool_calls), styles["Body"]))

        story.append(Paragraph("Duration", styles["Label"]))
        story.append(Paragraph(f"{r['duration_seconds']}s", styles["Body"]))

        if r.get("error"):
            story.append(Paragraph("Error", styles["Label"]))
            story.append(Paragraph(escape(r["error"]), ParagraphStyle("Err", parent=styles["Body"], textColor=FAIL_COLOR)))


def build_pdf(
    reports: list[dict],
    out_path: Path,
    comparison_csv: Path | None = None,
    comparison_plot: Path | None = None,
) -> None:
    """Render one eval section per entry in `reports` (each the same shape as
    evals/results.json), followed by an optional Model Comparison section."""
    styles, base_font, bold_font = build_styles()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    story = []
    for i, report in enumerate(reports):
        if i > 0:
            story.append(PageBreak())
        add_eval_section(
            story,
            styles,
            base_font,
            bold_font,
            heading_for(report["results"]),
            report["generated_at"],
            report["results"],
        )

    if comparison_csv is not None and comparison_csv.exists():
        story.append(PageBreak())
        add_comparison_section(story, styles, base_font, bold_font, comparison_csv, comparison_plot)

    doc.build(story)


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main(
    json_path: Path = EVALS_DIR / "results.json",
    out_path: Path = EVALS_DIR / "report.pdf",
    comparison_csv: Path = EVALS_DIR / "model_comparison.csv",
    comparison_plot: Path = EVALS_DIR / "model_comparison.png",
) -> Path:
    """Discover result files under `json_path`'s directory and render the PDF."""
    evals_dir = json_path.parent

    # If compare_models.py has run, it left one results_<model>.json per model
    # (same schema as run_evals.py --json); use those so every model gets its
    # own detail section instead of just the primary --json model.
    per_model_paths = sorted(evals_dir.glob("results_*.json"), key=lambda p: p.stat().st_mtime)
    if per_model_paths:
        report_paths = per_model_paths
    elif json_path.exists():
        report_paths = [json_path]
    else:
        raise SystemExit(
            f"{json_path} not found. Run `python3 evals/run_evals.py --json` first."
        )

    reports = [json.loads(p.read_text()) for p in report_paths]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(reports, out_path, comparison_csv, comparison_plot)
    print(f"Wrote {out_path} ({len(reports)} eval section(s): {', '.join(p.name for p in report_paths)})")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=EVALS_DIR / "results.json", help="Path to results.json")
    parser.add_argument("--out", type=Path, default=EVALS_DIR / "report.pdf", help="Path to write the PDF")
    parser.add_argument(
        "--comparison-csv",
        type=Path,
        default=EVALS_DIR / "model_comparison.csv",
        help="Path to compare_models.py's CSV output; section is skipped if missing",
    )
    parser.add_argument(
        "--comparison-plot",
        type=Path,
        default=EVALS_DIR / "model_comparison.png",
        help="Path to compare_models.py's chart",
    )
    args = parser.parse_args()
    main(args.json, args.out, args.comparison_csv, args.comparison_plot)
