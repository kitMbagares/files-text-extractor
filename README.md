## About

File-Extractor is a FastAPI backend that allows users to upload files, extract text/tables/images from them, and correct the text using language tools. Supports PDFs, images (OCR), Word documents, Excel spreadsheets, and CSV files.

## Supported File Types

| File Type | Extensions | Capabilities |
|---|---|---|
| PDF | `.pdf` | Text extraction, table extraction, image extraction, OCR (scanned PDFs) |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp` | OCR text extraction |
| Word | `.docx` | Text extraction |
| Excel | `.xlsx` | Spreadsheet data extraction |
| CSV | `.csv` | Data extraction |

## Getting Started

### Prerequisites

- Python 3.12+
- FastAPI, pdfplumber, PyMuPDF, python-docx, openpyxl, Pillow
- **For OCR:** [Tesseract](https://github.com/tesseract-ocr/tesseract) must be installed on your system

### Installation

1. Clone the repository:

  ```sh
  git clone https://github.com/arij01/PDF-Extractor.git
  cd PDF-Extractor
  ```
2. Install Python requirements:

  ```sh
  pip install -r requirements.txt
  ```
3. Install Tesseract for OCR (optional):

  ```sh
  # macOS
  brew install tesseract

  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr

  # Windows - download installer from https://github.com/tesseract-ocr/tesseract
  ```

## Running the Application

1. Create a `.env` file:

  ```sh
  API_KEY=your-secret
  HOST=127.0.0.1
  PORT=8001
  ALLOWED_ORIGINS=http://localhost:3000
  OCR_PROVIDER=local
  ```
2. Start the backend server:

  ```sh
  python3 app.py
  ```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | (required) | Bearer token for authentication |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |
| `OCR_PROVIDER` | `local` | OCR provider: `local` (Tesseract) or `none` (disabled) |

## API Usage

### Upload Endpoint

```
POST /upload/?mode=text&correct=true
Authorization: Bearer your-secret
Content-Type: multipart/form-data

file: <your file>
```

### URL Extraction Endpoint

```
POST /extract-url/?correct=true
Authorization: Bearer your-secret
Content-Type: application/json

{
  "url": "https://example.com/jobs/software-engineer"
}
```

### Query Parameters

| Parameter | Default | Options | Description |
|---|---|---|---|
| `mode` | `text` | `text`, `tables`, `images`, `ocr`, `full` | Extraction mode (PDF only) |
| `correct` | `true` | `true`, `false` | Apply grammar/spelling correction |

### Extraction Modes (PDF)

- **`text`** - Extract selectable text (auto-falls back to OCR if text is empty)
- **`tables`** - Extract tabular data
- **`images`** - Extract embedded images as base64
- **`ocr`** - Force OCR extraction (for scanned PDFs)
- **`full`** - Extract text + tables + images all at once

### Response Format

```json
{
  "filename": "document.pdf",
  "file_type": "pdf",
  "mode": "text",
  "extracted_text": "The extracted text content...",
  "corrected_text": "The grammar-corrected text...",
  "tables": null,
  "images": null,
  "metadata": {
    "used_ocr": false,
    "language_detected": "en"
  }
}
```

### Examples

**Extract text from a PDF:**
```sh
curl -X POST "http://localhost:8000/upload/?mode=text" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@document.pdf"
```

**Extract tables from a PDF:**
```sh
curl -X POST "http://localhost:8000/upload/?mode=tables" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@spreadsheet.pdf"
```

**Extract everything from a PDF:**
```sh
curl -X POST "http://localhost:8000/upload/?mode=full" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@document.pdf"
```

**OCR an image file:**
```sh
curl -X POST "http://localhost:8000/upload/" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@screenshot.png"
```

**Extract from a Word document:**
```sh
curl -X POST "http://localhost:8000/upload/" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@report.docx"
```

**Extract from an Excel file:**
```sh
curl -X POST "http://localhost:8000/upload/" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -F "file=@data.xlsx"
```

**Extract text from a job URL:**
```sh
curl -X POST "http://localhost:8000/extract-url/?correct=false" \
  -H "Authorization: Bearer T8zwjzSzc9R12lUFw8LeuhKZ6BIJd-ITsq6SvuQQVNI" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/jobs/software-engineer"}'
```
