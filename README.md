# LUXAN 2026 Katalog Q&A

Chat interface for asking technical questions about LUXAN 2026 product catalogues (blinds, rollers, jalousies, window coverings). Answers in German, English, or Polish.

## How It Works

1. **PDF Scanning** — `scan_catalogues.py` uses GPT-4o vision to extract product data from PDF catalogue pages into structured JSON files (one per catalogue).

2. **Two-Stage Retrieval** — When a user asks a question:
   - **Stage 1** (gpt-4o-mini): A compact index of all catalogues is used to select the 1-3 most relevant ones.
   - **Stage 2** (gpt-4o): The full JSON data of selected catalogues is injected into the prompt for an accurate, cited answer.

3. **Accuracy First** — `temperature=0` on both stages, strict rules to never invent data, mandatory page citations.

## Setup

```bash
pip install -r requirements.txt
```

Requires an `OPENAI_API_KEY`. The app loads it automatically from `../Converter/.env`, or you can set it as an environment variable.

## Usage

### Start the Q&A chat server

```bash
bash run.sh
# Opens at http://localhost:8000
```

### Scan PDF catalogues (extract product data)

Place PDF files in the project root and run:

```bash
python3 scan_catalogues.py
```

The scanner:
- Processes every page via GPT-4o vision
- Saves progress after each page (safe to interrupt and resume)
- Outputs `*.json` files next to the source PDFs
- Skips already-completed pages on restart

## Project Structure

```
app/
    __init__.py           # Package init
    server.py             # FastAPI server (/api/chat, /api/catalogues)
    retrieval.py          # JSON loading, catalogue index, data retrieval
    prompts.py            # GPT system/user prompt templates
    static/
        index.html        # Chat UI (vanilla HTML/CSS/JS)
scan_catalogues.py        # PDF-to-JSON extractor using GPT-4o vision
run.sh                    # Startup script
requirements.txt          # Python dependencies
```

## Catalogues

| Catalogue | Products | Status |
|-----------|----------|--------|
| Jalousien 50/35 | Blinds 50mm & 35mm (I50, I35, A50 series) | Done |
| Rollo | Roller blinds (R1-R4, XL, Mini, Dachfenster) | Done |
| Holzjalousien | Wooden blinds | In progress |
| Jalousien Ultimate | Premium blinds | Pending |
| Plisse | Pleated blinds | Pending |
| Raffrollo | Roman blinds | Pending |
| Vertikal | Vertical blinds | Pending |

## Languages

The chat accepts questions in:
- **Deutsch** — "Welche maximale Breite hat das Modell I50 S?"
- **English** — "What colors are available for the R4 Kassette?"
- **Polski** — "Jakie kolory są dostępne dla modelu I50 E?"

Product names, SKUs, and technical terms are always kept in original German.
