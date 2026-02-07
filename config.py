"""
config.py — Application settings and constants.

Loads environment variables and defines shared configuration
used across all modules (file type maps, size limits, OCR settings).
"""

import os
import shutil
import logging
from dotenv import load_dotenv

# ── Load .env file ──────────────────────────────────────────────────
load_dotenv()

# ── Logging ─────────────────────────────────────────────────────────
# Only log ERROR-level and above to keep output clean.
# All modules share this logger under the "extract_kit" namespace.
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("extract_kit")

# ── Server settings ─────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# ── CORS ────────────────────────────────────────────────────────────
# Comma-separated list of allowed origins, e.g. "http://localhost:3000,https://myapp.com"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# ── OCR settings ────────────────────────────────────────────────────
# "local" = use Tesseract binary on this machine
# "none"  = disable OCR entirely (for Vercel or environments without Tesseract)
OCR_PROVIDER = os.getenv("OCR_PROVIDER", "local")

# Check if the Tesseract binary exists on the system PATH
TESSERACT_AVAILABLE = shutil.which("tesseract") is not None

# ── File upload limits ──────────────────────────────────────────────
# Maximum upload size in bytes (default: 50MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))

# ── File type mapping ──────────────────────────────────────────────
# Maps file extensions to internal type identifiers used for routing
EXTENSION_MAP = {
    # Documents
    "pdf": "pdf",
    "docx": "docx",
    # Images (processed via OCR)
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "tiff": "image",
    "tif": "image",
    "bmp": "image",
    "webp": "image",
    # Spreadsheets
    "xlsx": "xlsx",
    "csv": "csv",
}

# ── Mode validation ────────────────────────────────────────────────
# Which extraction modes are valid for each file type.
# PDFs support all modes; other types only support "text" (auto-routed).
VALID_MODES_PER_TYPE = {
    "pdf": {"text", "tables", "images", "ocr", "full"},
    "image": {"text"},
    "docx": {"text"},
    "xlsx": {"text"},
    "csv": {"text"},
}
