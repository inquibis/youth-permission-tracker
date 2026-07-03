@echo off
REM Quick test runner script for API unit tests (Windows)

setlocal enabledelayedexpansion

echo ==========================================
echo Youth Permission Tracker - API Unit Tests
echo ==========================================
echo.

REM Check if pytest is installed
pytest --version > nul 2>&1
if errorlevel 1 (
    echo.❌ pytest not found. Installing test dependencies...
    pip install -r test-requirements.txt
)

echo.
echo.📋 Running API Unit Tests...
echo.

REM Run tests with coverage
pytest tests\unit\api\ ^
    -v ^
    --tb=short ^
    --cov=api_base ^
    --cov-report=term-missing ^
    --color=yes

echo.
echo.✅ Test run complete!
echo.

endlocal
pause
