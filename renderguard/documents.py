from __future__ import annotations

import hashlib
import json
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

IBAN_LENGTHS = {
    "DE": 22,
    "NL": 18,
    "CZ": 24,
    "AT": 20,
    "FR": 27,
    "BE": 16,
    "PL": 28,
    "ES": 24,
    "IT": 27,
    "SK": 24,
    "IE": 22,
    "GB": 22,
}


def normalize_iban(value: str) -> str:
    return re.sub(r"\s", "", value).upper()


def valid_iban(value: str) -> bool:
    value = normalize_iban(value)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", value):
        return False
    if len(value) != IBAN_LENGTHS.get(value[:2], -1):
        return False
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in value[4:] + value[:4])
    return int(numeric) % 97 == 1


def find_ibans(text: str) -> list[str]:
    values = []
    for line in text.upper().splitlines():
        for match in re.finditer(r"\b([A-Z]{2})\s*\d{2}", line):
            country = match.group(1)
            length = IBAN_LENGTHS.get(country)
            if not length:
                continue
            suffix = line[match.start() :]
            chars = []
            for c in suffix:
                if c in " \t":
                    continue
                if not c.isascii() or not c.isalnum():
                    break
                chars.append(c)
                if len(chars) == length:
                    break
            value = "".join(chars)
            if len(value) == length:
                values.append(value)
    return list(dict.fromkeys(values))


def money_minor(value: str) -> int | None:
    value = value.replace(" ", "").replace("\u00a0", "")
    if not re.fullmatch(r"-?[\d.,]+", value):
        return None
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            if not re.fullmatch(r"-?\d{1,3}(?:\.\d{3})*,\d{2}", value):
                return None
            value = value.replace(".", "").replace(",", ".")
        else:
            if not re.fullmatch(r"-?\d{1,3}(?:,\d{3})*\.\d{2}", value):
                return None
            value = value.replace(",", "")
    elif "," in value:
        if not re.fullmatch(r"-?\d+,\d{2}", value):
            return None
        value = value.replace(",", ".")
    elif not re.fullmatch(r"-?\d+(?:\.\d{2})?", value):
        return None
    try:
        amount = Decimal(value) * 100
        return int(amount) if amount == amount.to_integral_value() else None
    except InvalidOperation:
        return None


def fields(text: str) -> dict:
    totals, currencies, invoices, obligations = [], [], [], []
    for line in text.splitlines():
        total = re.search(
            r"(?:amount\s+due|invoice\s+total|total\s+due|grand\s+total|\btotal)\s*[: ]*([A-Z]{3})\s+(-?[\d][\d,. ]*)",
            line,
            re.I,
        )
        if total:
            currencies.append(total.group(1).upper())
            amount = money_minor(total.group(2).strip())
            if amount is not None:
                totals.append(amount)
        invoice = re.search(
            r"\binvoice(?:\s+(?:no\.?|number|#))?\s*[:#]?\s*([A-Z]{1,8}[-/][A-Z0-9/-]{2,35})", line, re.I
        )
        if invoice:
            invoices.append(invoice.group(1).upper())
        obligations.extend(re.findall(r"\bPO-\d{4}-\d{3}\b", line.upper()))
    return {
        "ibans": find_ibans(text),
        "amounts_minor": list(dict.fromkeys(totals)),
        "currencies": list(dict.fromkeys(currencies)),
        "invoice_numbers": list(dict.fromkeys(invoices)),
        "obligation_ids": list(dict.fromkeys(obligations)),
    }


def parse_epc(payload: str) -> dict:
    lines = payload.replace("\r", "").split("\n")
    if len(lines) < 8 or lines[0] != "BCD" or lines[3] != "SCT":
        return {
            "supported": False,
            "reason": "Not an EPC SEPA credit-transfer QR code",
            "payload": payload[:1000],
        }
    amount = lines[7]
    currency = amount[:3] if amount else None
    return {
        "supported": lines[1] in ("001", "002"),
        "name": lines[5],
        "iban": normalize_iban(lines[6]),
        "currency": currency,
        "amount_minor": money_minor(amount[3:]) if amount else None,
        "reference": (lines[9] if len(lines) > 9 and lines[9] else lines[10] if len(lines) > 10 else ""),
        "payload": payload[:1000],
    }


def process_pdf(folder: Path, max_pages: int = 5) -> dict:
    import pypdfium2 as pdfium
    import pytesseract
    import zxingcpp
    from pypdf import PdfReader

    started = time.monotonic()
    source = folder / "input.pdf"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    reader = PdfReader(source, strict=False)
    if reader.is_encrypted:
        raise ValueError("Password-protected invoices require an unlocked copy")
    count = len(reader.pages)
    if count < 1 or count > max_pages:
        raise ValueError(f"Supported invoices have 1–{max_pages} pages")
    pdf = pdfium.PdfDocument(str(source))
    pages, visible, raw, qrs = [], [], [], []
    for index in range(count):
        page = pdf[index]
        width, height = page.get_size()
        scale = min(2.2, 2600 / max(width, height))
        image = page.render(scale=scale).to_pil().convert("RGB")
        image_path = folder / f"page-{index + 1}.png"
        image.save(image_path)
        raw_text = page.get_textpage().get_text_range()
        if len(raw_text) > 100000:
            raise ValueError("PDF text layer exceeds processing limit")
        ocr = pytesseract.image_to_data(
            image, config="--psm 3", output_type=pytesseract.Output.DICT, timeout=20
        )
        groups = {}
        for i, word in enumerate(ocr["text"]):
            if not word.strip():
                continue
            key = (ocr["block_num"][i], ocr["par_num"][i], ocr["line_num"][i])
            groups.setdefault(key, []).append(
                {
                    "text": word,
                    "confidence": float(ocr["conf"][i]),
                    "left": ocr["left"][i],
                    "top": ocr["top"][i],
                    "width": ocr["width"][i],
                    "height": ocr["height"][i],
                }
            )
        lines = []
        for words in groups.values():
            left = min(w["left"] for w in words)
            top = min(w["top"] for w in words)
            right = max(w["left"] + w["width"] for w in words)
            bottom = max(w["top"] + w["height"] for w in words)
            lines.append(
                {
                    "text": " ".join(w["text"] for w in words),
                    "confidence": sum(w["confidence"] for w in words) / len(words),
                    "box": [
                        left / image.width,
                        top / image.height,
                        (right - left) / image.width,
                        (bottom - top) / image.height,
                    ],
                    "page": index + 1,
                }
            )
        visible_text = "\n".join(line["text"] for line in lines)
        page_qrs = []
        for code in zxingcpp.read_barcodes(image):
            qr = parse_epc(code.text)
            pos = code.position
            points = [pos.top_left, pos.top_right, pos.bottom_right, pos.bottom_left]
            x1, y1 = min(p.x for p in points), min(p.y for p in points)
            x2, y2 = max(p.x for p in points), max(p.y for p in points)
            qr.update(
                {
                    "page": index + 1,
                    "box": [
                        x1 / image.width,
                        y1 / image.height,
                        (x2 - x1) / image.width,
                        (y2 - y1) / image.height,
                    ],
                }
            )
            page_qrs.append(qr)
        pages.append(
            {
                "page": index + 1,
                "width": image.width,
                "height": image.height,
                "render_hash": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "lines": lines,
                "raw_text": raw_text,
                "visible_text": visible_text,
                "visible_fields": fields(visible_text),
                "raw_fields": fields(raw_text),
                "qr_codes": page_qrs,
            }
        )
        visible.append(visible_text)
        raw.append(raw_text)
        qrs.extend(page_qrs)
        page.close()
    pdf.close()
    return {
        "source_hash": source_hash,
        "pages": pages,
        "visible": fields("\n".join(visible)),
        "machine": fields("\n".join(raw)),
        "visible_text": "\n".join(visible),
        "machine_text": "\n".join(raw),
        "qr_codes": qrs,
        "processing_ms": round((time.monotonic() - started) * 1000),
        "ocr_engine": "Tesseract, rendered pixels",
        "renderer": "PDFium (no V8)",
        "schema_version": 1,
    }


def write_result(folder: Path, value: dict):
    target = folder / "result.json"
    temp = folder / "result.tmp"
    temp.write_text(json.dumps(value, ensure_ascii=False))
    temp.replace(target)
