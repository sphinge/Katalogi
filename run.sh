#!/usr/bin/env bash
# Start the LUXAN Catalogue Q&A server

set -e

cd "$(dirname "$0")"

# Load API key from Converter/.env if not already set
if [ -z "$OPENAI_API_KEY" ]; then
    ENV_FILE="../Converter/.env"
    if [ -f "$ENV_FILE" ]; then
        export $(grep '^OPENAI_API_KEY=' "$ENV_FILE" | xargs)
        echo "Loaded OPENAI_API_KEY from $ENV_FILE"
    fi
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY is not set and not found in ../Converter/.env"
    exit 1
fi

echo "Starting LUXAN Catalogue Q&A on http://localhost:8000"
python3 -m uvicorn app.server:app --host 0.0.0.0 --port 8000
