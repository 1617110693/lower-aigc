"""Build a DOCX file from paragraphs with style information."""

import io
import logging

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

from app.schemas.document import StyleInfo

logger = logging.getLogger(__name__)

ALIGNMENT_REVERSE_MAP = {
    0: WD_ALIGN_PARAGRAPH.LEFT,
    1: WD_ALIGN_PARAGRAPH.CENTER,
    2: WD_ALIGN_PARAGRAPH.RIGHT,
    3: WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def build_docx(paragraphs: list[dict]) -> io.BytesIO:
    """
    Build a .docx file from paragraph data.

    Each paragraph dict should have:
      - text (str): the text content (prefer reduced_text over original_text)
      - style_info (dict | None): formatting information
    """
    doc = DocxDocument()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Times New Roman"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    for para_data in paragraphs:
        text = para_data.get("text", "")
        style_info_raw = para_data.get("style_info")

        if style_info_raw:
            style_info = StyleInfo.model_validate(style_info_raw)
            _add_paragraph_with_style(doc, text, style_info)
        else:
            doc.add_paragraph(text)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    logger.info(f"Built DOCX with {len(paragraphs)} paragraphs")
    return buf


def _add_paragraph_with_style(doc: DocxDocument, text: str, style: StyleInfo):
    """Add a paragraph to the document with the specified style."""
    if style.is_heading and style.heading_level:
        level = min(style.heading_level, 9)
        doc.add_heading(text, level=level)
        return

    para = doc.add_paragraph()

    # Paragraph alignment
    if style.alignment is not None and style.alignment in ALIGNMENT_REVERSE_MAP:
        para.alignment = ALIGNMENT_REVERSE_MAP[style.alignment]

    # Line spacing
    if style.line_spacing:
        para.paragraph_format.line_spacing = style.line_spacing

    # First line indent
    if style.first_line_indent:
        para.paragraph_format.first_line_indent = Pt(style.first_line_indent)

    # Add text run with formatting
    run = para.add_run(text)
    if style.font_name:
        run.font.name = style.font_name
        # Also set East Asian font
        run._element.rPr.rFonts.set(qn("w:eastAsia"), style.font_name)
    if style.font_size:
        run.font.size = Pt(style.font_size)
    run.bold = style.bold
    run.italic = style.italic
    run.underline = style.underline
