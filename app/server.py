"""FastAPI server — serves the chat UI and handles the two-stage GPT retrieval."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from .prompts import STAGE1_SYSTEM, STAGE1_USER, STAGE2_SYSTEM, STAGE2_USER
from .retrieval import CatalogueStore

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load OPENAI_API_KEY: check local .env first, then ../Converter/.env
_local_env = PROJECT_ROOT / ".env"
_converter_env = PROJECT_ROOT.parent / "Converter" / ".env"
for _env_file in (_local_env, _converter_env):
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
        break

app = FastAPI(title="LUXAN Catalogue Q&A")

STATIC_DIR = Path(__file__).resolve().parent / "static"

print("Loading catalogues...")
store = CatalogueStore(PROJECT_ROOT)
print(f"Ready — {len(store.catalogues)} catalogue(s) loaded.\n")

client = OpenAI()  # uses OPENAI_API_KEY env var


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]  # catalogue filenames used


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/catalogues")
async def list_catalogues():
    return store.list_catalogues()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question is empty.")

    if not store.catalogues:
        return ChatResponse(answer="No catalogue data is loaded. Place JSON catalogue files in the project root.", sources=[])

    # --- Stage 1: pick relevant catalogues ---
    index_text = store.get_full_index()

    stage1_resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": STAGE1_SYSTEM},
            {"role": "user", "content": STAGE1_USER.format(index=index_text, question=question)},
        ],
    )

    raw = stage1_resp.choices[0].message.content.strip()
    try:
        selected_files = json.loads(raw)
        if not isinstance(selected_files, list):
            selected_files = [raw]
    except json.JSONDecodeError:
        # Fallback: use all catalogues
        selected_files = list(store.catalogues.keys())

    # --- Stage 2: answer with full data ---
    catalogue_data, matched_files = store.get_catalogue_data(selected_files)

    if not matched_files:
        # Fallback: send all catalogues
        catalogue_data, matched_files = store.get_catalogue_data(list(store.catalogues.keys()))

    # Build conversation messages
    messages = [
        {"role": "system", "content": STAGE2_SYSTEM.format(catalogue_data=catalogue_data)},
    ]

    # Add conversation history (last 12 messages)
    for msg in req.history[-12:]:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": STAGE2_USER.format(question=question)})

    stage2_resp = client.chat.completions.create(
        model="o3",
        messages=messages,
    )

    answer = stage2_resp.choices[0].message.content

    return ChatResponse(answer=answer, sources=matched_files)


# Serve static files (CSS, JS if any)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
