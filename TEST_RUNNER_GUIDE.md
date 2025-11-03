# 🧪 Test Runner Guide

## Quick Start

Run all tests with one command:

```bash
# Option 1: Using npm script
npm run test:all

# Option 2: Using Node.js directly
node run-all-tests.js

# Option 3: Using batch script (Windows)
run-tests.bat

# Option 4: Using PowerShell (Windows)
.\run-tests.ps1
```

## What Gets Tested

The test runner executes the following test suites in order:

### 1. Configuration Check ✅
- Validates `vite.config.ts`
- Checks `package.json`
- Verifies `index.html` and `src/main.ts`
- Validates `node_modules` status

**Duration**: ~1 second

### 2. E2E UI Tests (Playwright) 🌐
Tests the complete application in real browsers:

**Browsers Tested:**
- ✅ Desktop Chrome/Edge (Chromium)
- ✅ Desktop Firefox
- ✅ Desktop Safari (WebKit)
- ✅ Mobile Chrome (Pixel 5)
- ✅ Mobile Safari (iPhone 12)

**Features Tested:**
- Application startup
- Player management (add, remove, validation)
- Session creation (Round Robin, King of Court)
- Match operations (complete, forfeit, scoring)
- Rankings and statistics
- Data persistence (localStorage)
- Locked teams functionality
- UI interactions and modals

**Test Count**: 70+ tests × 5 browsers = 350+ test cases

**Duration**: ~3-4 minutes

### 3. Unit Tests (Vitest) 🔬
Tests core algorithms and logic:

**Coverage:**
- Round Robin algorithm
- King of the Court logic
- Player management functions
- Match scheduling
- Queue management
- Wait time calculations

**Status**: Automatically skipped if no unit tests exist

**Duration**: ~10-30 seconds (if present)

## Output Format

The test runner provides clear, color-coded output:

```
🧪 PICKLEBALL SESSION MANAGER - COMPREHENSIVE TEST SUITE
Started at: 11/3/2025, 2:19:24 AM

============================================================
📋 Step 1: Configuration Check
============================================================

▶️  Configuration Validation
   Command: node check-config.js

✅ Configuration Validation - PASSED (0.23s)

============================================================
🌐 Step 2: End-to-End UI Tests (Playwright)
============================================================

Testing in real browsers: Chromium, Firefox, WebKit, Mobile

▶️  E2E UI Tests (All Browsers)
   Command: npx -y playwright@latest test --reporter=list

[Test execution output...]

✅ E2E UI Tests (All Browsers) - PASSED (187.45s)

============================================================
🔬 Step 3: Unit Tests (Vitest)
============================================================

ℹ️  No unit tests found - skipping

============================================================
📊 TEST RESULTS SUMMARY
============================================================

✅ 1. Configuration Validation
   Status: PASSED (0.23s)

✅ 2. E2E UI Tests (All Browsers)
   Status: PASSED (187.45s)

ℹ️  3. Unit Tests (skipped - not found)
   Status: SKIPPED (0s)

────────────────────────────────────────────────────────────
Total: 3 test suites
Passed: 2
Skipped: 1
Duration: 187.68s
────────────────────────────────────────────────────────────

🎉 ALL TESTS PASSED! 🎉
Your Pickleball Session Manager is ready to deploy! 🎾
```

## Exit Codes

- `0` - All tests passed
- `1` - Configuration check failed or tests failed

## Running Individual Test Suites

### E2E Tests Only

```bash
# All browsers, headless
npx playwright test

# With interactive UI
npx playwright test --ui

# Single browser
npx playwright test --project=chromium

# Specific test file
npx playwright test tests/e2e/01-setup.spec.ts

# Debug mode
npx playwright test --debug
```

### Unit Tests Only

```bash
# Run once
npm run test:run

# Watch mode
npm test

# With UI
npm run test:ui
```

### Configuration Check Only

```bash
node check-config.js
```

## Help and Documentation

View help:

```bash
node run-all-tests.js --help
```

## Continuous Integration

The test runner works great in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run all tests
  run: npm run test:all
```

The script automatically detects CI environments and adjusts:
- Retries: 2 attempts in CI
- Workers: Single worker in CI
- Output: List reporter in CI

## Test Reports

### E2E Test Report

After running E2E tests:

```bash
npx playwright show-report
```

Opens an interactive HTML report with:
- Test results
- Screenshots (on failure)
- Videos (on failure)
- Traces
- Timing information

### Unit Test Report

Unit test results are shown in the terminal.

## Troubleshooting

### Configuration Check Fails

**Issue**: Config validation fails before tests run

**Solution**: 
```bash
# Check the specific error
node check-config.js

# Common fixes:
# - Remove invalid imports from vite.config.ts
# - Ensure index.html and src/main.ts exist
```

### E2E Tests Fail

**Issue**: Browser tests failing

**Solution**:
```bash
# Install Playwright browsers
npx playwright install

# Run with UI to debug
npx playwright test --ui

# Check specific browser
npx playwright test --project=chromium
```

### Port Already in Use

**Issue**: `Error: Port 5173 already in use`

**Solution**:
```bash
# Kill the process using port 5173
# Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Or let Playwright reuse the server
# (Already configured in playwright.config.ts)
```

### Tests Timeout

**Issue**: Tests taking too long or timing out

**Solution**: Increase timeouts in `playwright.config.ts`:
```typescript
use: {
  actionTimeout: 15000,      // Increase from 10000
  navigationTimeout: 45000,  // Increase from 30000
}
```

### Dev Server Won't Start

**Issue**: Server fails to start during tests

**Solution**:
```bash
# Test server manually first
npx -y vite@latest

# If it works, the test runner should work too
```

## Performance Expectations

**Typical Run Times:**

| Test Suite | Duration | Tests |
|------------|----------|-------|
| Config Check | ~1s | 1 |
| E2E (all browsers) | ~3-4min | 350+ |
| Unit Tests | ~10-30s | Varies |
| **Total** | **~4-5min** | **350+** |

**Hardware Impact:**
- CPU: Heavy during E2E tests (5 browsers in parallel)
- RAM: ~2-4GB during test execution
- Disk: Minimal (logs and reports)

## Best Practices

### Before Committing

Always run all tests:
```bash
npm run test:all
```

### Before Deploying

Run tests and check results:
```bash
npm run test:all
npx playwright show-report
```

### During Development

Run specific test suites:
```bash
# Quick E2E check (single browser)
npx playwright test --project=chromium

# Watch mode for unit tests
npm test
```

### Debugging Failures

Use interactive modes:
```bash
# E2E with UI
npx playwright test --ui

# E2E with debug
npx playwright test --debug

# Unit tests with UI
npm run test:ui
```

## Integration with Pre-commit Hooks

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/sh
echo "Running tests before commit..."
npm run test:all

if [ $? -ne 0 ]; then
  echo "Tests failed! Commit aborted."
  exit 1
fi
```

## What's Next

After all tests pass:

1. ✅ **Build**: `npm run build`
2. ✅ **Deploy**: `npm run deploy`
3. ✅ **Celebrate**: Your app is production-ready! 🎉

## Summary

- ✅ One command runs everything: `npm run test:all`
- ✅ Clear, color-coded output
- ✅ Automatic dev server management
- ✅ Comprehensive test coverage
- ✅ CI/CD ready
- ✅ Multiple execution options

**Run tests regularly to ensure quality!** 🧪🎾
