"""Catalogue data loading, indexing, and retrieval."""

import json
from pathlib import Path


class CatalogueStore:
    """Loads JSON catalogues and provides index + full-data retrieval."""

    def __init__(self, data_dir: str | Path = "."):
        self.data_dir = Path(data_dir)
        self.catalogues: dict[str, dict] = {}  # filename -> parsed JSON
        self._load_all()

    def _load_all(self) -> None:
        for path in sorted(self.data_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Only load files that look like catalogue data
                if "pages" in data and "total_products" in data:
                    self.catalogues[path.name] = data
                    print(f"  Loaded: {path.name} ({data['total_products']} products, {data['total_pages']} pages)")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  Skipped {path.name}: {e}")

    def get_full_index(self) -> str:
        """Build a compact index string for Stage 1 catalogue selection."""
        if not self.catalogues:
            return "No catalogues loaded."

        parts = []
        for filename, data in self.catalogues.items():
            product_names: set[str] = set()
            categories: set[str] = set()
            descriptions: set[str] = set()

            for page in data.get("pages", []):
                for product in page.get("products", []):
                    if name := product.get("name"):
                        if isinstance(name, list):
                            product_names.update(name)
                        else:
                            product_names.add(str(name))
                    if cat := product.get("category"):
                        if isinstance(cat, list):
                            categories.update(cat)
                        else:
                            categories.add(str(cat))
                    if desc := product.get("description"):
                        if isinstance(desc, str) and len(desc) < 80:
                            descriptions.add(desc)

            # Separate short model names (key identifiers) from long accessory names
            model_names = sorted(n for n in product_names if len(n) <= 30)
            other_names = sorted(n for n in product_names if len(n) > 30)

            entry = (
                f"FILE: {filename}\n"
                f"  Source PDF: {data.get('source_file', 'unknown')}\n"
                f"  Total products: {data['total_products']}, Total pages: {data['total_pages']}\n"
                f"  Key models: {', '.join(model_names[:80])}\n"
            )
            if other_names:
                entry += f"  Other products: {', '.join(other_names[:30])}\n"
            if categories:
                entry += f"  Categories: {', '.join(sorted(categories))}\n"
            if descriptions:
                entry += f"  Descriptions: {', '.join(sorted(descriptions)[:20])}\n"
            parts.append(entry)

        return "\n".join(parts)

    def get_catalogue_data(self, filenames: list[str]) -> tuple[str, list[str]]:
        """Return full JSON for selected catalogues with image_description stripped.

        Returns (data_string, list_of_matched_filenames).
        """
        matched = []
        parts = []

        for fname in filenames:
            if fname in self.catalogues:
                matched.append(fname)
                parts.append(self._strip_catalogue(fname))

        return "\n\n---\n\n".join(parts), matched

    def _strip_catalogue(self, filename: str) -> str:
        """Return catalogue JSON as string with image_description removed to save tokens."""
        data = self.catalogues[filename]
        stripped = {
            "source_file": data.get("source_file", filename),
            "total_pages": data.get("total_pages"),
            "total_products": data.get("total_products"),
            "pages": [],
        }
        for page in data.get("pages", []):
            stripped_page = {
                "page_number": page.get("page_number"),
                "page_notes": page.get("page_notes", ""),
                "products": [],
            }
            for product in page.get("products", []):
                p = {k: v for k, v in product.items() if k != "image_description"}
                stripped_page["products"].append(p)
            stripped["pages"].append(stripped_page)

        return json.dumps(stripped, ensure_ascii=False, indent=None)

    def list_catalogues(self) -> list[dict]:
        """Return summary list of available catalogues."""
        result = []
        for filename, data in self.catalogues.items():
            result.append({
                "filename": filename,
                "source_pdf": data.get("source_file", ""),
                "total_products": data.get("total_products", 0),
                "total_pages": data.get("total_pages", 0),
            })
        return result
