#!/usr/bin/env pwsh

<#
.SYNOPSIS
    Comprehensive Test Runner for Pickleball Session Manager
    
.DESCRIPTION
    Runs all tests: E2E UI tests, Unit tests, and Integration tests
    
.EXAMPLE
    .\run-tests.ps1
    
.EXAMPLE
    pwsh -File run-tests.ps1
#>

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " PICKLEBALL SESSION MANAGER - COMPREHENSIVE TEST SUITE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Run the Node.js test script
node run-all-tests.js

# Exit with the same code
exit $LASTEXITCODE
