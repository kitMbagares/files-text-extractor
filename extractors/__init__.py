"""
extractors/ — File extraction modules.

Each module handles a specific file type:
  - pdf.py         : PDF text, tables, images, page count
  - ocr.py         : OCR for images and scanned PDFs (requires Tesseract)
  - docx_ext.py    : Word document (.docx) text extraction
  - spreadsheet.py : Excel (.xlsx) and CSV data extraction
"""
