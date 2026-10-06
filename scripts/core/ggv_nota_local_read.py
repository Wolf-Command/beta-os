"""Local, no-spend document reading for GGV nota images.

Uses macOS on-device Vision (Live Text) when available, then tesseract.
No metered APIs. Extraction proposals only — never accounting truth.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_HELPERS = Path(__file__).resolve().parents[1] / "helpers"
_SWIFT_SRC = _HELPERS / "ggv_nota_vision_ocr.swift"
_VISION_BIN = _HELPERS / "ggv_nota_vision_ocr"


def _vision_binary() -> Path | None:
    """Use a pre-built helper only — compile at deploy, not on first upload."""
    if sys.platform != "darwin":
        return None
    if _VISION_BIN.is_file() and os.access(_VISION_BIN, os.X_OK):
        return _VISION_BIN
    return None


def _read_vision(data: bytes) -> tuple[str, dict[str, Any]]:
    binary = _vision_binary()
    if not binary:
        return "", {"reader": "macos_vision", "available": False}
    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        proc = subprocess.run(
            [str(binary), path],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        meta = {"reader": "macos_vision", "available": True, "ok": False}
        if isinstance(exc, subprocess.TimeoutExpired):
            meta["timeout"] = True
        else:
            meta["error"] = type(exc).__name__
        return "", meta
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if proc.returncode != 0:
        return "", {
            "reader": "macos_vision",
            "available": True,
            "ok": False,
            "stderr": (proc.stderr or "").strip()[:240],
        }
    text = (proc.stdout or "").strip()
    return text, {"reader": "macos_vision", "available": True, "ok": True, "char_count": len(text)}


def _read_tesseract(data: bytes) -> tuple[str, dict[str, Any]]:
    if not shutil.which("tesseract"):
        return "", {"reader": "tesseract", "available": False}
    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        proc = subprocess.run(
            ["tesseract", path, "stdout", "-l", "eng+ind"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        meta = {"reader": "tesseract", "available": True, "ok": False}
        if isinstance(exc, subprocess.TimeoutExpired):
            meta["timeout"] = True
        else:
            meta["error"] = type(exc).__name__
        return "", meta
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if proc.returncode != 0:
        return "", {
            "reader": "tesseract",
            "available": True,
            "ok": False,
            "stderr": (proc.stderr or "").strip()[:240],
        }
    text = (proc.stdout or "").strip()
    return text, {"reader": "tesseract", "available": True, "ok": True, "char_count": len(text)}


def read_image_bytes(data: bytes) -> tuple[str, dict[str, Any]]:
    """Return OCR text and reader metadata. Empty text is valid (not an error)."""
    if os.environ.get("GGV_NOTA_OCR_FIXTURE"):
        fixture = Path(os.environ["GGV_NOTA_OCR_FIXTURE"])
        if fixture.is_file():
            text = fixture.read_text(encoding="utf-8")
            return text, {"reader": "fixture", "available": True, "ok": True, "char_count": len(text)}
    text, meta = _read_vision(data)
    if text.strip():
        return text, meta
    ttext, tmeta = _read_tesseract(data)
    if ttext.strip():
        return ttext, tmeta
    # Prefer vision meta when both ran but returned nothing.
    if meta.get("available"):
        return "", {**meta, "fallback": tmeta.get("reader")}
    return "", tmeta
