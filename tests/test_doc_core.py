"""Offline tests for the doc connector: bindings, engine report, text extraction, graceful no-OCR."""
import urirun_connector_doc.core as c


def test_bindings_valid():
    b = c.urirun_bindings()
    assert set(b["bindings"]) == {
        "doc://host/file/query/text", "doc://host/file/query/ocr", "doc://host/engine/query/list"}
    # the **kw schema bug must stay fixed: engines() takes no required props
    eng = b["bindings"]["doc://host/engine/query/list"]["inputSchema"]
    assert not eng.get("required")


def test_engines_reports_tools():
    e = c.engines()
    assert e["ok"]
    assert "pdftotext" in e["tools"] and "tesseract" in e["tools"]
    assert "rapidocr" in e["ocrEngines"]


def test_text_from_plain_file(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("Faktura FV 7/2026 kwota 1230 PLN", encoding="utf-8")
    r = c.file_text(path=str(p))
    assert r["ok"] and r["engine"] == "raw"
    assert "Faktura FV 7/2026" in r["text"]
    # Shared urirun.tag contract: extracted text is a frozen artifact.
    assert r["kind"] == "text" and r["live"] is False


def test_missing_file():
    assert c.file_text(path="/no/such/file.pdf")["ok"] is False


def test_image_with_ocr_off_is_rejected(tmp_path):
    p = tmp_path / "scan.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n")  # not a real image, but routed as image → ocr=off path
    r = c.file_text(path=str(p), ocr="off")
    assert r["ok"] is False
    assert "ocr=off" in r["error"]


def test_max_chars_truncation(tmp_path):
    p = tmp_path / "big.txt"
    p.write_text("x" * 5000, encoding="utf-8")
    r = c.file_text(path=str(p), max_chars=100)
    assert r["chars"] == 100
