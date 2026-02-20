#!/usr/bin/env bash
# Start the LUXAN Catalogue Q&A server

set -e

cd "$(dirname "$0")"

# Load API key: check local .env first, then ../Converter/.env
if [ -z "$OPENAI_API_KEY" ]; then
    for ENV_FILE in ".env" "../Converter/.env"; do
        if [ -f "$ENV_FILE" ]; then
            export $(grep '^OPENAI_API_KEY=' "$ENV_FILE" | xargs)
            echo "Loaded OPENAI_API_KEY from $ENV_FILE"
            break
        fi
    done
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY is not set."
    echo "Create a .env file with: OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

echo "Starting LUXAN Catalogue Q&A on http://localhost:8000"
python3 -m uvicorn app.server:app --host 0.0.0.0 --port 8000
