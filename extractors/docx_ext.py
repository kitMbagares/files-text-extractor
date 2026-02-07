"""
extractors/docx_ext.py — Word document (.docx) extraction.

Uses python-docx to read paragraphs from .docx files.
Named docx_ext.py (not docx.py) to avoid shadowing the 'docx' package.
"""

import io
from fastapi import HTTPException
from docx import Document

from config import logger


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract all paragraph text from a .docx file.

    Skips empty paragraphs. Returns paragraphs joined by newlines.
    Raises 422 if the file is not a valid .docx.
    """
    try:
        doc = Document(io.BytesIO(file_bytes))
        # Filter out blank paragraphs for cleaner output
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.exception("Error extracting text from docx")
        raise HTTPException(status_code=422, detail=f"Failed to read DOCX file: {e}")
