@echo off
REM Comprehensive Test Runner for Windows
REM Runs all tests: E2E, Unit, Integration

echo.
echo ============================================================
echo  PICKLEBALL SESSION MANAGER - COMPREHENSIVE TEST SUITE
echo ============================================================
echo.

REM Run the Node.js test script
node run-all-tests.js

REM Pass exit code
exit /b %ERRORLEVEL%
