"""Parse DOCX files into paragraphs with style information."""

import logging
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.schemas.document import StyleInfo

logger = logging.getLogger(__name__)

ALIGNMENT_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: 0,
    WD_ALIGN_PARAGRAPH.CENTER: 1,
    WD_ALIGN_PARAGRAPH.RIGHT: 2,
    WD_ALIGN_PARAGRAPH.JUSTIFY: 3,
}


def parse_docx(file_path: str | Path) -> list[dict]:
    """
    Parse a .docx file and extract paragraphs with style information.

    Returns a list of dicts with keys: index, text, style_info.
    Skips empty paragraphs.
    """
    doc = DocxDocument(str(file_path))
    paragraphs = []

    index = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_info = extract_style_info(para)
        paragraphs.append({
            "index": index,
            "text": text,
            "style_info": style_info.model_dump(),
        })
        index += 1

    logger.info(f"Parsed {len(paragraphs)} non-empty paragraphs from {file_path}")
    return paragraphs


def extract_docx_title(file_path: str | Path) -> str | None:
    """Try to extract a title from the document properties or first heading."""
    doc = DocxDocument(str(file_path))

    # Try core properties title
    if doc.core_properties.title:
        return doc.core_properties.title

    # Try first heading-style paragraph
    for para in doc.paragraphs:
        if para.style.name.startswith("Heading") and para.text.strip():
            return para.text.strip()

    return None


def extract_style_info(para) -> StyleInfo:
    """Extract formatting information from a python-docx paragraph."""
    # Paragraph-level formatting
    alignment = None
    if para.alignment is not None:
        alignment = ALIGNMENT_MAP.get(para.alignment)

    line_spacing = None
    if para.paragraph_format.line_spacing:
        line_spacing = float(para.paragraph_format.line_spacing)

    first_line_indent = None
    if para.paragraph_format.first_line_indent:
        first_line_indent = para.paragraph_format.first_line_indent.pt

    # Check if it's a heading
    is_heading = para.style.name.startswith("Heading") if para.style else False
    heading_level = None
    if is_heading:
        try:
            heading_level = int(para.style.name.replace("Heading", "").strip())
        except ValueError:
            heading_level = 1

    # Run-level formatting (take from the first run)
    font_name = None
    font_size = None
    bold = False
    italic = False
    underline = False

    if para.runs:
        first_run = para.runs[0]
        if first_run.font.name:
            font_name = first_run.font.name
        if first_run.font.size:
            font_size = first_run.font.size.pt
        bold = bool(first_run.bold)
        italic = bool(first_run.italic)
        underline = bool(first_run.underline)

    return StyleInfo(
        font_name=font_name,
        font_size=font_size,
        bold=bold,
        italic=italic,
        underline=underline,
        alignment=alignment,
        line_spacing=line_spacing,
        first_line_indent=first_line_indent,
        is_heading=is_heading,
        heading_level=heading_level,
    )
