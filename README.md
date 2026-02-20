# LUXAN 2026 Katalog Q&A

Chat interface for asking technical questions about LUXAN 2026 product catalogues (blinds, rollers, jalousies, window coverings). Answers in German, English, or Polish.

## How It Works

1. **PDF Scanning** — `scan_catalogues.py` uses GPT-4o vision to extract product data from PDF catalogue pages into structured JSON files (one per catalogue).

2. **Two-Stage Retrieval** — When a user asks a question:
   - **Stage 1** (gpt-4o-mini): A compact index of all catalogues is used to select the 1-3 most relevant ones.
   - **Stage 2** (o3): The full JSON data of selected catalogues is injected into the prompt for an accurate, cited answer.

3. **Accuracy First** — Strict rules to never invent data, mandatory page citations in every answer.

## Setup

### 1. Install Python

Requires **Python 3.10+**. Check with:

```
python --version
```

On Linux/Mac you may need to use `python3` instead of `python`.

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Set up your OpenAI API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-your-key-here
```

Or set it as an environment variable:

- **Windows (cmd):** `set OPENAI_API_KEY=sk-your-key-here`
- **Windows (PowerShell):** `$env:OPENAI_API_KEY="sk-your-key-here"`
- **Linux/Mac:** `export OPENAI_API_KEY=sk-your-key-here`

## Running the Q&A Chat Server

### Windows

Double-click `run.bat`, or from the command prompt:

```
run.bat
```

### Linux / Mac

```bash
bash run.sh
```

Then open **http://localhost:8000** in your browser.

## Scanning PDF Catalogues

To extract product data from new PDF catalogues, place the PDF files in the project root and run:

```
python scan_catalogues.py
```

On Linux/Mac use `python3` if needed.

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
run.bat                   # Windows startup script
run.sh                    # Linux/Mac startup script
requirements.txt          # Python dependencies
.env                      # Your OpenAI API key (create this yourself)
```

## Catalogues

| Catalogue | Description | Pages | Products |
|-----------|-------------|-------|----------|
| Jalousien 50/35 | Blinds 50mm & 35mm (I50, I35, A50 series) | 122 | 388 |
| Rollo | Roller blinds (R1-R4, XL, Mini, Dachfenster) | 160 | 410 |
| Holzjalousien | Wooden blinds (H50, H65 series) | 76 | 276 |
| Jalousien Ultimate | Premium blinds | 88 | 263 |
| Plisse | Pleated blinds | 216 | 476 |
| Raffrollo | Roman blinds | 46 | 133 |
| Vertikal | Vertical blinds | 66 | 164 |
| **Total** | | **774** | **2,110** |

## Languages

The chat accepts questions in:
- **Deutsch** — "Welche maximale Breite hat das Modell I50 S?"
- **English** — "What colors are available for the R4 Kassette?"
- **Polski** — "Jakie kolory są dostępne dla modelu I50 E?"

Product names, SKUs, and technical terms are always kept in original German.

## Troubleshooting

**"OPENAI_API_KEY not set"** — Create a `.env` file in the project root with `OPENAI_API_KEY=sk-your-key-here`.

**"No module named 'fastapi'"** — Run `pip install -r requirements.txt` first.

**Server starts but chat returns errors** — Check that your OpenAI API key is valid and has access to gpt-4o-mini and o3 models.

**`python` not found on Linux/Mac** — Use `python3` instead, e.g. `python3 -m uvicorn app.server:app --host 0.0.0.0 --port 8000`.
