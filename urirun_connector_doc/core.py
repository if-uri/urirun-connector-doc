# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# doc:// connector — first-class URI document text extraction / OCR, so classifying
# invoices (and any scan/PDF) no longer needs shell:// + pdftotext by hand. Text-layer
# PDFs go through `pdftotext` (fast, exact); scans/images fall back through an OCR chain
# that reuses existing engines when present: tesseract, RapidOCR (the wronai/img2nl ONNX
# engine — no system binary), or an Ollama vision model (wronai/ocr). Everything degrades
# gracefully: with only pdftotext on the node you still extract every text-layer PDF, and
# the response says exactly which engine ran (or why OCR was unavailable).

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any

import urirun

CONNECTOR_ID = "doc"
DOC = urirun.connector(CONNECTOR_ID, scheme="doc", target="host", meta={"label": "Document text / OCR"})

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif")


def _run(cmd: list[str], timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _pdftotext(path: str, layout: bool = True) -> str:
    """Exact text of a text-layer PDF via poppler's pdftotext (no OCR)."""
    if not shutil.which("pdftotext"):
        return ""
    args = ["pdftotext"] + (["-layout"] if layout else []) + [path, "-"]
    try:
        r = _run(args, timeout=120)
        return r.stdout if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _pdf_to_images(path: str, outdir: str, dpi: int = 200) -> list[str]:
    """Rasterise a (scanned) PDF to PNG pages using whatever is on the node: pdftoppm
    (poppler) first, then `pdfimages`, then ImageMagick `magick`."""
    base = os.path.join(outdir, "page")
    if shutil.which("pdftoppm"):
        _run(["pdftoppm", "-r", str(dpi), "-png", path, base], timeout=300)
    elif shutil.which("pdfimages"):
        _run(["pdfimages", "-png", path, base], timeout=300)
    elif shutil.which("magick"):
        _run(["magick", "-density", str(dpi), path, base + ".png"], timeout=300)
    return sorted(os.path.join(outdir, f) for f in os.listdir(outdir) if f.lower().endswith(".png"))


# --- OCR engine chain: tesseract → RapidOCR (img2nl/onnx) → Ollama vision (wronai/ocr) ---

def _ocr_tesseract(img: str, lang: str) -> str | None:
    if not shutil.which("tesseract"):
        return None
    try:
        r = _run(["tesseract", img, "stdout", "-l", lang], timeout=120)
        return r.stdout if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def _ocr_rapidocr(img: str) -> str | None:
    """RapidOCR — the ONNX engine wronai/img2nl ships; no system binary, no tesseract.
    Reuse img2nl's wrapper if importable, else call rapidocr_onnxruntime directly."""
    try:
        from img2nl.features.ocr_text import analyze_ocr  # type: ignore
        from PIL import Image
        out = analyze_ocr(Image.open(img))
        lines = (out or {}).get("lines") or []
        if lines:
            return "\n".join(str(x) for x in lines)
    except Exception:  # noqa: BLE001
        pass
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
        res, _ = RapidOCR()(img)
        if res:
            return "\n".join(box[1] for box in res)
    except Exception:  # noqa: BLE001
        pass
    return None


def _ocr_ollama(img: str, model: str) -> str | None:
    """Ollama vision model (the wronai/ocr approach) if an Ollama daemon is up."""
    if not shutil.which("ollama"):
        return None
    try:
        from pdf_processor.processing.ocr_processor import OCRProcessor  # type: ignore
        return OCRProcessor(model=model).extract_text(img).text
    except Exception:  # noqa: BLE001
        pass
    try:
        r = _run(["ollama", "run", model, f"Transcribe all text in this image verbatim: {img}"], timeout=300)
        return r.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _ocr_image(img: str, lang: str, model: str) -> tuple[str, str]:
    """Try the OCR engines in order; return (text, engine)."""
    for name, fn in (("tesseract", lambda: _ocr_tesseract(img, lang)),
                     ("rapidocr", lambda: _ocr_rapidocr(img)),
                     ("ollama", lambda: _ocr_ollama(img, model))):
        text = fn()
        if text and text.strip():
            return text, name
    return "", "none"


@DOC.handler("file/query/text", isolated=True,
             meta={"label": "Extract text from a PDF/image (pdftotext, OCR fallback)", "cliAlias": "text"})
def file_text(path: str = "", ocr: str = "auto", min_text: int = 40, dpi: int = 200,
              lang: str = "pol+eng", model: str = "llava:7b", max_chars: int = 0) -> dict[str, Any]:
    """Text of a document at `path`. Text-layer PDFs use pdftotext; if that yields fewer than
    `min_text` chars (a scan) and ocr in {auto,on}, pages are rasterised and OCR'd. Images go
    straight to OCR. `ocr`: auto (default) | on (force) | off (never). Returns {text, engine}."""
    path = os.path.expanduser(path)
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": f"file not found: {path}"}
    ext = os.path.splitext(path)[1].lower()
    engine = "none"
    text = ""
    if ext == ".pdf":
        text = _pdftotext(path) if ocr != "on" else ""
        engine = "pdftotext" if text.strip() else "none"
        if ocr != "off" and len(text.strip()) < min_text:
            with tempfile.TemporaryDirectory() as td:
                pages = _pdf_to_images(path, td, dpi=dpi)
                otext, oeng = [], "none"
                for p in pages:
                    t, e = _ocr_image(p, lang, model)
                    if t:
                        otext.append(t); oeng = e
                if otext:
                    text, engine = "\n\n".join(otext), oeng
    elif ext in _IMAGE_EXTS:
        if ocr == "off":
            return {"ok": False, "error": "image needs OCR but ocr=off", "path": path}
        text, engine = _ocr_image(path, lang, model)
    else:
        # plain text / unknown → read as utf-8 best-effort
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
            engine = "raw"
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "path": path}
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]
    return {"ok": bool(text.strip()), "connector": CONNECTOR_ID, "path": path,
            "ext": ext, "engine": engine, "chars": len(text), "text": text}


@DOC.handler("file/query/ocr", isolated=True,
             meta={"label": "Force OCR on a PDF/image (skip the text layer)", "cliAlias": "ocr"})
def file_ocr(path: str = "", dpi: int = 200, lang: str = "pol+eng", model: str = "llava:7b",
             max_chars: int = 0) -> dict[str, Any]:
    """Force the OCR chain even on a text-layer PDF (for scans embedded in a PDF wrapper)."""
    return file_text(path=path, ocr="on", dpi=dpi, lang=lang, model=model, max_chars=max_chars)


@DOC.handler("engine/query/list", isolated=True, meta={"label": "Which extract/OCR engines are available"})
def engines() -> dict[str, Any]:
    """Report the document tools present on this node, so a planner knows what will run."""
    def have(mod: str) -> bool:
        try:
            __import__(mod); return True
        except Exception:  # noqa: BLE001
            return False
    return {"ok": True, "connector": CONNECTOR_ID, "tools": {
        "pdftotext": bool(shutil.which("pdftotext")), "pdftoppm": bool(shutil.which("pdftoppm")),
        "pdfimages": bool(shutil.which("pdfimages")), "magick": bool(shutil.which("magick")),
        "tesseract": bool(shutil.which("tesseract")), "ollama": bool(shutil.which("ollama"))},
        "ocrEngines": {"tesseract": bool(shutil.which("tesseract")),
                       "rapidocr": have("rapidocr_onnxruntime") or have("img2nl"),
                       "ollama": bool(shutil.which("ollama"))}}


def main(argv: list[str] | None = None) -> int:
    return DOC.cli(argv, manifest_prose=urirun.load_manifest(__package__))


urirun_bindings = DOC.bindings
