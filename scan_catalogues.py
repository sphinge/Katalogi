#!/usr/bin/env python3
"""
Scan PDF catalogues using GPT-4o vision and extract product information to JSON.

Usage:
    python scan_catalogues.py [FOLDER_PATH]

If no folder path is given, scans the current directory.
Looks for PDF files in all subdirectories recursively.
Outputs one JSON file per PDF (same name, .json extension) next to the original PDF.
"""

import sys
import os
import json
import base64
import time
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL = "gpt-4o"
MAX_TOKENS = 4096
DPI = 200  # Resolution for rendering PDF pages to images
IMAGE_FORMAT = "png"

SYSTEM_PROMPT = """You are a precise data extractor for LUXAN 2026 product catalogues (blinds, rollers, jalousies, window coverings).

You will receive an image of a single catalogue page. Extract ALL information with maximum accuracy.

EXTRACTION PRIORITIES (extract every one you can see):

1. DIMENSIONS — This is critical. Extract ALL of these when visible:
   - min_width (minimale Breite) — often different per configuration (e.g. LR/RL vs LL/RR)
   - max_width (maximale Breite)
   - min_height (minimale Höhe)
   - max_height (maximale Höhe)
   - max_area (maximale Fläche, m²)
   - Always include the unit (cm, mm, m²)

2. PRODUCT IDENTIFICATION:
   - name: exact model name as printed (e.g. "Modell I50 S", "R4 Rollo mit Kassette 80 mm")
   - sku: article/reference number
   - description: product description, operation type (Schnurzug, Endlosschnur, Kurbel, Elektrisch, etc.)
   - category: product category or section header

3. TECHNICAL SPECIFICATIONS — extract ALL visible specs into the "specifications" object:
   - Materials (Aluminium, Kunststoff, Stahlseil, etc.)
   - Lamella/slat size (e.g. 50 mm, 35 mm)
   - Operation type and details
   - Mounting options (Wandmontage, Deckenmontage, Klemmträger, etc.)
   - Fabric weight limits (g/m²) and corresponding max dimensions
   - Tube sizes (RTU-28, RTU-42, etc.)
   - Package heights (Pakethöhen)
   - Any min/max constraints or conditions

4. COLORS — extract ALL color options:
   - Lamella colors (Lamellenfarben) with codes
   - Rail/track colors (Schienenfarben)
   - System colors (Kunststoff)
   - RAL numbers if shown

5. PRICES — extract ALL pricing:
   - Fixed prices with currency (e.g. "38,00 €")
   - Per-unit prices (e.g. "8,10 €/Lfm", "16,20 €/Paar")
   - Percentage surcharges (e.g. "15%", "200% PGO")
   - Price grid descriptions (if a price table is visible, describe its structure: what the rows/columns represent, the range of values)

6. ACCESSORIES & OPTIONS:
   - Optional features with surcharges (Texband, Seitenführung, etc.)
   - Motor/electrical options with model numbers and prices
   - Mounting accessories

Return a JSON object:
{
  "products": [
    {
      "name": "...",
      "sku": "...",
      "description": "...",
      "price": "...",
      "category": "...",
      "brand": "...",
      "specifications": {},
      "colors": {},
      "image_description": "...",
      "additional_info": "..."
    }
  ],
  "page_notes": "any general page info, section headers, footnotes, or conditions"
}

Rules:
- Only include fields that are actually visible on the page. Omit fields with no data.
- Extract EVERY number, dimension, and specification visible — do not summarize or skip.
- Keep all text in its original language (German). Do not translate.
- If a table is visible, extract its complete content — every row and column.
- If the page has no products (e.g. cover, TOC), return {"products": [], "page_notes": "..."}.
- Return ONLY valid JSON, no markdown fences, no extra text."""


def render_page_to_base64(page: fitz.Page) -> str:
    """Render a PDF page to a base64-encoded PNG."""
    pix = page.get_pixmap(dpi=DPI)
    img_bytes = pix.tobytes(IMAGE_FORMAT)
    return base64.b64encode(img_bytes).decode("utf-8")


def extract_products_from_page(client: OpenAI, image_b64: str, page_num: int, pdf_name: str) -> dict:
    """Send a page image to GPT-4o and get structured product data back."""
    print(f"    Processing page {page_num}...", end=" ", flush=True)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Extract all product information from this catalogue page (page {page_num} of '{pdf_name}').",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{IMAGE_FORMAT};base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if GPT wraps the response
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("WARNING: could not parse JSON, storing raw response")
        data = {"raw_response": raw, "products": [], "page_notes": "Failed to parse structured data"}

    product_count = len(data.get("products", []))
    print(f"found {product_count} product(s)")
    return data


def save_result(result: dict, json_path: Path):
    """Write the current result to the JSON file."""
    total_products = sum(len(p.get("products", [])) for p in result["pages"])
    result["total_products"] = total_products
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def load_existing_result(json_path: Path) -> dict | None:
    """Load an existing partial JSON result if it exists."""
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def process_pdf(client: OpenAI, pdf_path: Path) -> dict:
    """Process all pages of a single PDF, saving after each page."""
    print(f"\n  Opening: {pdf_path.name}")
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    print(f"  Pages: {total_pages}")

    json_path = pdf_path.with_suffix(".json")

    # Resume from existing progress if available
    existing = load_existing_result(json_path)
    if existing and existing.get("source_file") == pdf_path.name:
        result = existing
        done_pages = {p["page_number"] for p in result.get("pages", [])}
        print(f"  Resuming: {len(done_pages)} page(s) already processed, skipping them")
    else:
        result = {
            "source_file": str(pdf_path.name),
            "total_pages": total_pages,
            "pages": [],
        }
        done_pages = set()

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        if page_num in done_pages:
            continue

        page = doc[page_idx]
        image_b64 = render_page_to_base64(page)
        page_data = extract_products_from_page(client, image_b64, page_num, pdf_path.name)
        page_data["page_number"] = page_num
        result["pages"].append(page_data)

        # Save after every page
        save_result(result, json_path)

    doc.close()

    total_products = sum(len(p.get("products", [])) for p in result["pages"])
    result["total_products"] = total_products
    print(f"  Done: {total_products} total product(s) extracted from {pdf_path.name}")
    return result


def find_pdfs(folder: Path) -> list[Path]:
    """Recursively find all PDF files in a folder."""
    pdfs = sorted(folder.rglob("*.pdf"))
    pdfs += sorted(p for p in folder.rglob("*.PDF") if p not in pdfs)
    return pdfs


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    folder = folder.resolve()

    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory.")
        sys.exit(1)

    # Load API key: check local .env first, then ../Converter/.env
    local_env = folder / ".env"
    converter_env = folder / ".." / "Converter" / ".env"
    for env_file in (local_env, converter_env):
        if env_file.exists():
            load_dotenv(env_file, override=False)
            break

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Create a .env file with: OPENAI_API_KEY=sk-your-key-here")
        print("Or set it as an environment variable.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    pdfs = find_pdfs(folder)
    if not pdfs:
        print(f"No PDF files found in '{folder}'.")
        sys.exit(0)

    print(f"Found {len(pdfs)} PDF file(s) in '{folder}':")
    for p in pdfs:
        print(f"  - {p.relative_to(folder)}")

    for pdf_path in pdfs:
        start = time.time()
        result = process_pdf(client, pdf_path)
        elapsed = time.time() - start
        print(f"  Saved: {pdf_path.with_suffix('.json').name} ({elapsed:.1f}s)")

    print("\nAll done!")


if __name__ == "__main__":
    main()
