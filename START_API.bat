@echo off
REM Youth Permission Tracker - API Startup Script
REM This script starts the FastAPI server for the Youth Data Editor

echo Starting Youth Permission Tracker API...
echo.
echo Make sure you're in the workspace root directory (c:\sandbox\youth-permission-tracker)
echo.

cd /d c:\sandbox\youth-permission-tracker

REM Activate Python environment if needed
if exist sandbox\Scripts\activate.bat (
    call sandbox\Scripts\activate.bat
    echo Python environment activated.
    echo.
)

REM Start the API
echo Starting API server on http://localhost:5000
echo.
echo Once the server starts, open your browser to:
echo   http://localhost:5000/website/youth_editor.html
echo or
echo   file:///c:/sandbox/youth-permission-tracker/website/youth_editor.html
echo.
echo Press Ctrl+C to stop the server.
echo.

python run_local.py

pause
