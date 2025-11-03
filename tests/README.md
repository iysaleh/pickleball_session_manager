# 🧪 Comprehensive UI Testing Guide

This project includes comprehensive end-to-end (E2E) UI tests using Playwright that run in real browsers.

## 📋 Test Coverage

The test suite covers all major features:

### Test Files

1. **01-setup.spec.ts** - Application initialization and setup
   - Page loading
   - Theme toggle
   - Initial state
   - Form elements
   - Default values

2. **02-player-management.spec.ts** - Player operations
   - Adding players
   - Removing players
   - Input validation
   - Enter key support
   - Multiple players

3. **03-session-start.spec.ts** - Starting sessions
   - Round-robin sessions
   - King-of-court sessions
   - Singles/doubles modes
   - Court configuration
   - Auto-starting matches

4. **04-match-management.spec.ts** - Match operations
   - Completing matches
   - Score validation
   - Forfeiting matches
   - Match history
   - Waiting players

5. **05-rankings-stats.spec.ts** - Rankings and statistics
   - Rankings modal
   - Statistics modal
   - Modal interactions
   - Data display
   - Match history

6. **06-local-storage.spec.ts** - Data persistence
   - Session persistence
   - Player persistence
   - Theme persistence
   - Banned pairs
   - Clear data functionality

7. **07-locked-teams.spec.ts** - Team management
   - Locked teams mode
   - Adding teams
   - Removing teams
   - Team validation
   - Session with teams

## 🚀 Running Tests

### Prerequisites

```bash
npm install
```

This will install Playwright and all dependencies.

### Install Playwright Browsers (First Time Only)

```bash
npx playwright install
```

This downloads Chromium, Firefox, and WebKit browsers.

### Run All Tests

```bash
npm run test:e2e
```

This runs all tests in headless mode (no browser window).

### Run Tests with UI

```bash
npm run test:e2e:ui
```

Opens Playwright UI with:
- Visual test runner
- Time travel debugging
- Watch mode
- Test results

### Run Tests in Headed Mode

```bash
npm run test:e2e:headed
```

Shows actual browser windows while tests run.

### Debug Tests

```bash
npm run test:e2e:debug
```

Opens Playwright Inspector for step-by-step debugging.

### Run Specific Test File

```bash
npx playwright test tests/e2e/01-setup.spec.ts
```

### Run Specific Test

```bash
npx playwright test tests/e2e/01-setup.spec.ts -g "should load the application"
```

## 🌐 Browser Configuration

Tests run on multiple browsers by default:

- **Chromium** (Chrome/Edge)
- **Firefox**
- **WebKit** (Safari)
- **Mobile Chrome** (Pixel 5 emulation)
- **Mobile Safari** (iPhone 12 emulation)

To run on specific browser:

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
npx playwright test --project="Mobile Chrome"
```

## 📊 Test Reports

After running tests, view the HTML report:

```bash
npx playwright show-report
```

This opens an interactive report with:
- Test results
- Screenshots
- Videos (for failures)
- Trace files
- Execution timeline

## 🐛 Debugging Failed Tests

When a test fails:

1. **Check the console output** - Shows which assertion failed
2. **View screenshots** - Automatically captured on failure
3. **Watch videos** - Recorded for failed tests
4. **Use trace viewer** - Visual timeline of test execution

```bash
npx playwright show-trace playwright-report/trace.zip
```

## 📝 Writing New Tests

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/');
  });

  test('should do something', async ({ page }) => {
    // Test steps
    await page.click('#button');
    
    // Assertions
    await expect(page.locator('#result')).toBeVisible();
  });
});
```

### Common Patterns

```typescript
// Navigate
await page.goto('/');

// Fill input
await page.fill('#player-name', 'John');

// Click button
await page.click('#add-player-btn');

// Select dropdown
await page.selectOption('#game-mode', 'round-robin');

// Check checkbox
await page.check('#locked-teams-checkbox');

// Wait for element
await page.waitForSelector('.court', { timeout: 5000 });

// Assertions
await expect(page.locator('#element')).toBeVisible();
await expect(page.locator('#element')).toHaveText('Expected');
await expect(page.locator('#element')).toContainText('Partial');
await expect(page.locator('#element')).toHaveValue('Value');
```

### Best Practices

1. **Clear localStorage before each test**
   ```typescript
   test.beforeEach(async ({ page }) => {
     await page.goto('/');
     await page.evaluate(() => localStorage.clear());
     await page.reload();
   });
   ```

2. **Use test IDs** - Prefer `#id` selectors over classes

3. **Wait appropriately** - Use `waitForSelector` for dynamic content

4. **Handle dialogs** - Accept alerts/confirms
   ```typescript
   page.on('dialog', dialog => dialog.accept());
   ```

5. **Test user flows** - Test complete workflows, not just individual actions

## 🎯 Test Coverage Goals

Current coverage:

- ✅ Setup and initialization
- ✅ Player management
- ✅ Session creation
- ✅ Match management
- ✅ Rankings and statistics
- ✅ Local storage persistence
- ✅ Locked teams mode
- ✅ Theme switching
- ✅ Modal interactions
- ✅ Form validation

## 🔧 Configuration

Edit `playwright.config.ts` to customize:

- Test directory
- Timeout values
- Browser options
- Base URL
- Screenshot/video settings
- Reporter options

## 📚 Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
- [Selectors](https://playwright.dev/docs/selectors)

## 🆘 Troubleshooting

### Tests fail to start

```bash
# Reinstall browsers
npx playwright install --force
```

### Port 5173 in use

```bash
# Kill the process using port 5173
# Then run tests again
```

### Tests timeout

- Increase timeout in `playwright.config.ts`
- Check if dev server is running properly
- Ensure selectors are correct

### Flaky tests

- Add appropriate waits
- Use `waitForSelector` for dynamic content
- Check for race conditions

## 🎉 Continuous Integration

Tests are configured to run in CI environments with:
- Automatic retries (2 attempts)
- Single worker (no parallel)
- HTML reporter output

To run in CI mode:

```bash
CI=true npm run test:e2e
```

## 📈 Next Steps

To extend test coverage:

1. Add tests for queue management
2. Test more complex match scenarios
3. Add accessibility tests
4. Add performance tests
5. Test error conditions
6. Add visual regression tests

Happy Testing! 🧪🎾
