@echo off
echo ============================================
echo   World News + History App
echo ============================================
echo.

:: Check if ANTHROPIC_API_KEY is set
if "%ANTHROPIC_API_KEY%"=="" (
    echo ERROR: ANTHROPIC_API_KEY is not set!
    echo.
    echo Please set your API key:
    echo   set ANTHROPIC_API_KEY=your-key-here
    echo.
    echo Or paste your key below and press Enter:
    set /p ANTHROPIC_API_KEY=API Key:
    echo.
)

:: Install dependencies if needed
echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting server...
echo Open your browser at: http://localhost:5000
echo Press Ctrl+C to stop.
echo.
python app.py
pause
