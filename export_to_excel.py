
#!/usr/bin/env python3
"""
Create a single Excel file containing English and Marathi names plus other fields
by OCR-ing the ward PDFs.
"""

import argparse
import os
import re
import shutil
from typing import Dict, List, Optional

import pandas as pd
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path


EPIC_RE = re.compile(r"\b[A-Z]{3}\d{7}\b")
HOUSE_RE = re.compile(r"\b\d{1,4}/\d{1,4}/\d{1,4}\b")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def extract_first_after_label(lines: List[str], label_patterns: List[re.Pattern], skip_patterns: List[re.Pattern]) -> Optional[str]:
    for idx, line in enumerate(lines):
        if any(p.search(line) for p in label_patterns):
            for j in range(idx + 1, len(lines)):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if any(p.search(candidate) for p in skip_patterns):
                    continue
                return candidate
    return None


def split_name_by_script(name: str, current: Dict[str, Optional[str]]) -> None:
    if DEVANAGARI_RE.search(name):
        current["name_marathi"] = current.get("name_marathi") or name
    if LATIN_RE.search(name):
        current["name_english"] = current.get("name_english") or name


def extract_part_number(text: str) -> Optional[str]:
    # Try common OCR variants for "भाग क."
    for pattern in [r"भाग\s*क\.?\s*(\d+)", r"भभ?ग\s*क\.?\s*(\d+)"]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def parse_entries_from_text(text: str, ward: Optional[str], source_file: str) -> List[Dict[str, Optional[str]]]:
    cleaned = normalize_text(text)
    part_no = extract_part_number(cleaned)

    parts = re.split(r"\n\s*(\d{1,4})\s*\n", cleaned)
    rows: List[Dict[str, Optional[str]]] = []

    if len(parts) < 3:
        return rows

    for i in range(1, len(parts), 2):
        serial = parts[i].strip()
        chunk = parts[i + 1]

        lines = [ln.strip() for ln in chunk.split("\n") if ln.strip()]

        entry: Dict[str, Optional[str]] = {
            "ward": ward,
            "part": part_no,
            "serial": serial,
            "name_marathi": None,
            "name_english": None,
            "relation_name": None,
            "gender": None,
            "age": None,
            "house_no": None,
            "epic_no": None,
            "source_file": source_file,
        }

        age_name_match = re.search(r"(\d{1,3})\s*:::+\s*([^\n]+)", chunk)
        if age_name_match:
            entry["age"] = age_name_match.group(1)
            split_name_by_script(age_name_match.group(2).strip(), entry)

        epic_match = EPIC_RE.search(chunk)
        if epic_match:
            entry["epic_no"] = epic_match.group(0)

        house_match = HOUSE_RE.search(chunk)
        if house_match:
            entry["house_no"] = house_match.group(0)

        gender_match = re.search(r"(पुरुष|स्त्री|महिला|पुरूष|Male|Female)\b", chunk)
        if gender_match:
            entry["gender"] = gender_match.group(1)

        # Try to capture voter name and relation name via labels when OCR keeps them
        voter_label_patterns = [
            re.compile(r"मतदार.*नाव"),
            re.compile(r"नाव"),
            re.compile(r"Name"),
        ]
        relation_label_patterns = [
            re.compile(r"वडिल"),
            re.compile(r"वडील"),
            re.compile(r"पती"),
            re.compile(r"पत"),
            re.compile(r"Father"),
            re.compile(r"Husband"),
        ]
        skip_patterns = [
            re.compile(r"वय"),
            re.compile(r"घर"),
            re.compile(r"मतदार"),
            re.compile(r"Name"),
            re.compile(r"Age"),
        ]

        voter_name = extract_first_after_label(lines, voter_label_patterns, skip_patterns)
        if voter_name:
            split_name_by_script(voter_name, entry)

        relation_name = extract_first_after_label(lines, relation_label_patterns, skip_patterns)
        if relation_name:
            entry["relation_name"] = relation_name

        # Fallback: check any line containing EPIC and strip it to pick a second name
        if entry.get("epic_no"):
            for line in lines:
                if entry["epic_no"] in line:
                    cleaned_line = line.replace(entry["epic_no"], "")
                    if entry.get("house_no"):
                        cleaned_line = cleaned_line.replace(entry["house_no"], "")
                    cleaned_line = cleaned_line.strip()
                    if cleaned_line:
                        split_name_by_script(cleaned_line, entry)
                    break

        rows.append(entry)

    return rows


def ensure_binaries() -> None:
    if shutil.which("tesseract") is None:
        raise FileNotFoundError("tesseract not found. Install tesseract-ocr and tesseract-ocr-mar.")
    if shutil.which("pdftoppm") is None and shutil.which("pdftocairo") is None:
        raise FileNotFoundError("Poppler tools not found. Install poppler-utils.")


def ocr_pdf_to_rows(
    pdf_path: str,
    dpi: int,
    start_page: Optional[int],
    end_page: Optional[int],
    page_batch: int,
    tesseract_timeout: int,
) -> List[Dict[str, Optional[str]]]:
    ward_match = re.search(r"Ward_(\d+)", os.path.basename(pdf_path))
    ward = ward_match.group(1) if ward_match else None
    rows: List[Dict[str, Optional[str]]] = []

    info = pdfinfo_from_path(pdf_path)
    total_pages = int(info.get("Pages", 0))
    if total_pages == 0:
        return rows

    first_page = start_page or 1
    last_page = end_page or total_pages
    last_page = min(last_page, total_pages)

    for batch_start in range(first_page, last_page + 1, page_batch):
        batch_end = min(batch_start + page_batch - 1, last_page)
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=batch_start,
            last_page=batch_end,
        )
        for offset, image in enumerate(images):
            page_no = batch_start + offset
            print(f"OCR {os.path.basename(pdf_path)} page {page_no}/{last_page}...")
            text = pytesseract.image_to_string(
                image,
                lang="mar+eng",
                config="--psm 6",
                timeout=tesseract_timeout,
            )
            rows.extend(parse_entries_from_text(text, ward, os.path.basename(pdf_path)))

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export election list PDFs to a single Excel file.")
    parser.add_argument("--output", default="election_list.xlsx", help="Output Excel filename")
    parser.add_argument("--dpi", type=int, default=250, help="DPI for OCR rendering")
    parser.add_argument("--start-page", type=int, help="First page to OCR (1-based)")
    parser.add_argument("--end-page", type=int, help="Last page to OCR (1-based)")
    parser.add_argument("--page-batch", type=int, default=2, help="Pages to render per batch")
    parser.add_argument("--tesseract-timeout", type=int, default=60, help="OCR timeout per page (seconds)")
    args = parser.parse_args()

    ensure_binaries()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_files = [
        os.path.join(script_dir, "FinalList_Ward_2.pdf"),
        os.path.join(script_dir, "FinalList_Ward_3.pdf"),
    ]

    all_rows: List[Dict[str, Optional[str]]] = []
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"Missing PDF: {pdf_file}")
        all_rows.extend(
            ocr_pdf_to_rows(
                pdf_file,
                args.dpi,
                args.start_page,
                args.end_page,
                args.page_batch,
                args.tesseract_timeout,
            )
        )

    df = pd.DataFrame(all_rows)
    df.to_excel(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
