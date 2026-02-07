"""
text_utils.py — Text processing utilities.

Contains helper functions for:
  - Flattening table/spreadsheet data into readable text
  - Grammar and spelling correction via LanguageTool
"""

from langdetect import detect
from config import logger

# ── Lazy LanguageTool initialization ─────────────────────────────────
# LanguageTool requires Java and downloads a ~200MB server on first run.
# By initializing lazily, the app won't crash at startup if Java is missing.
# The tools are cached after first use so subsequent calls are fast.

_tool_en = None
_tool_fr = None


def _get_language_tool(lang: str):
    """Get or create a LanguageTool instance for the given language."""
    global _tool_en, _tool_fr
    import language_tool_python

    if lang == "fr":
        if _tool_fr is None:
            _tool_fr = language_tool_python.LanguageTool("fr")
        return _tool_fr
    else:
        if _tool_en is None:
            _tool_en = language_tool_python.LanguageTool("en-US")
        return _tool_en


# ── Table-to-text flattening ────────────────────────────────────────

def flatten_table_to_text(data) -> str:
    """
    Convert structured table data into pipe-delimited readable text.

    Handles three formats:
      - dict (XLSX): {"Sheet1": [["row"], ...]}  ->  "Sheet: Sheet1\nA | B"
      - list of dicts (PDF tables): [{"page": 1, "rows": [...]}]
      - list of lists (CSV): [["row1"], ["row2"]]
    """
    lines = []

    if isinstance(data, dict):
        # XLSX format: dict of sheet_name -> rows
        for sheet_name, rows in data.items():
            lines.append(f"Sheet: {sheet_name}")
            for row in rows:
                lines.append(" | ".join(row))
            lines.append("")

    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            # PDF table format: list of {page, table_index, rows}
            for table in data:
                lines.append(f"Table (page {table.get('page', '?')}):")
                for row in table.get("rows", []):
                    lines.append(" | ".join(row))
                lines.append("")
        else:
            # CSV format: flat list of rows
            for row in data:
                lines.append(" | ".join(row))

    return "\n".join(lines)


# ── Grammar correction ──────────────────────────────────────────────

def correct_text(text: str) -> str:
    """
    Auto-detect language and apply grammar/spelling correction.

    Supports English and French. Returns the original text unchanged
    if correction fails (e.g., Java not installed, text too short).
    """
    # Skip very short text — language detection needs at least a few words
    if not text or len(text.strip()) < 3:
        return text

    try:
        language = detect(text)
        tool = _get_language_tool(language)
        return tool.correct(text)
    except Exception:
        logger.exception("Error correcting text (grammar tool may be unavailable)")
        return text
