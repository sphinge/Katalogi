@echo off
REM Start the LUXAN Catalogue Q&A server on Windows

cd /d "%~dp0"

python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
if errorlevel 1 (
    echo.
    echo Failed to start. Make sure you have installed dependencies:
    echo   pip install -r requirements.txt
    echo.
    echo And created a .env file with your OpenAI API key:
    echo   OPENAI_API_KEY=sk-your-key-here
    pause
)
