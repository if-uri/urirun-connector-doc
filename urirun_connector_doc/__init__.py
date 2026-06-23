"""doc:// connector — URI document text extraction / OCR (pdftotext + OCR fallback chain)."""
from .core import DOC, file_text, file_ocr, engines, main, urirun_bindings

__all__ = ["DOC", "file_text", "file_ocr", "engines", "main", "urirun_bindings"]
