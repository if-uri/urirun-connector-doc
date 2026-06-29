# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Route contracts for the doc connector — file text/OCR extraction, read-only."""
from __future__ import annotations

from urirun_connectors_toolkit.contract_gate import Contract

_TEXT_OUT = {"ok": "bool", "text": "str", "method": "str", "pages": "int"}

CONTRACTS: dict[str, Contract] = {
    "file/query/text": Contract(
        version="v1",
        effect="query",
        reversible=False,
        inp={"path": "str", "ocr": "?str", "min_text": "?int", "dpi": "?int",
             "lang": "?str", "model": "?str", "max_chars": "?int"},
        out=_TEXT_OUT,
        errors=("precondition-unmet",),
        examples=(
            {
                "payload": {"path": "/tmp/test.pdf"},
                "result": {
                    "ok": True,
                    "connector": "doc",
                    "text": "Hello world",
                    "method": "pdfminer",
                    "pages": 1,
                },
            },
        ),
    ),
    "file/query/ocr": Contract(
        version="v1",
        effect="query",
        reversible=False,
        inp={"path": "str", "dpi": "?int", "lang": "?str", "model": "?str", "max_chars": "?int"},
        out=_TEXT_OUT,
        errors=("precondition-unmet",),
        examples=(
            {
                "payload": {"path": "/tmp/scan.jpg"},
                "result": {
                    "ok": True,
                    "connector": "doc",
                    "text": "Invoice 100 PLN",
                    "method": "tesseract",
                    "pages": 1,
                },
            },
        ),
    ),
    "engine/query/list": Contract(
        version="v1",
        effect="query",
        reversible=False,
        inp={},
        out={"ok": "bool", "engines": "list"},
        errors=(),
        examples=(
            {
                "payload": {},
                "result": {
                    "ok": True,
                    "connector": "doc",
                    "engines": ["pdfminer", "tesseract", "paddleocr"],
                },
            },
        ),
    ),
}
