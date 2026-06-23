# urirun-connector-doc

**Document text / OCR** — connector ekosystemu [ifURI / urirun](https://github.com/if-uri/urirun).
Schemat URI: `doc://`

Extract text from PDFs and images over doc:// URIs. Text-layer PDFs use pdftotext; scans/images fall back through an OCR chain (tesseract, RapidOCR/ONNX from wronai-img2nl, or an Ollama vision model from wronai-ocr). Degrades gracefully to pdftotext-only.

## Opis

doc:// turns document text extraction into a first-class URI instead of ad-hoc shell + pdftotext. doc://host/file/query/text returns the text of a PDF or image: a text-layer PDF goes through poppler pdftotext; a scan/image falls back to OCR, rasterising PDF pages (pdftoppm/pdfimages/magick) and running the first available engine — tesseract, then RapidOCR (the ONNX engine reused from wronai/img2nl, no system binary needed), then an Ollama vision model (reused from wronai/ocr). doc://host/file/query/ocr forces OCR; doc://host/engine/query/list reports which engines are present. Useful for classifying invoices and any scanned document over the mesh.

## Wymagania

- **system:** pdftotext (poppler) recommended; pdftoppm/pdfimages/magick for OCR rasterisation
- **python:** urirun
- **optional:** rapidocr-onnxruntime or img2nl for no-tesseract OCR; tesseract; ollama

## Instalacja (dev)

```bash
pip install -e .
pytest -q
```

## Powiązane

- Rdzeń: [if-uri/urirun](https://github.com/if-uri/urirun)
- Hub connectorów: [connect.ifuri.com](https://connect.ifuri.com)

---
Kategoria: Documents · Słowa kluczowe: ocr, pdf, pdftotext, rapidocr, tesseract, invoice, document, text · Wydawca: if-uri
