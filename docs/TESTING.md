# 🧪 Testing Guide - Quick Start

## Overview

This project includes **comprehensive UI tests** that run in real browsers using Playwright. The tests cover all major features and user workflows.

## ✨ What's Tested

- ✅ Application setup and initialization
- ✅ Player management (add, remove, validate)
- ✅ Session creation (all modes and types)
- ✅ Match management (complete, forfeit, scores)
- ✅ Rankings and statistics (modals, data display)
- ✅ Local storage persistence (auto-save, restore)
- ✅ Locked teams functionality
- ✅ Theme switching (dark/light mode)
- ✅ Modal interactions (open, close, backdrop)
- ✅ Form validation and user input

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Install Playwright Browsers (First Time)

```bash
npx playwright install
```

This downloads Chromium, Firefox, and WebKit browsers (~400MB total).

### 3. Run Tests

#### Run All Tests (Headless)
```bash
npm run test:e2e
```

#### Run with Visual UI (Recommended)
```bash
npm run test:e2e:ui
```

This opens an interactive UI where you can:
- See all tests
- Run individual tests
- Watch tests execute
- Time-travel debug
- View results

#### Run with Browser Visible
```bash
npm run test:e2e:headed
```

#### Debug Mode
```bash
npm run test:e2e:debug
```

## 📊 View Results

After running tests:

```bash
npx playwright show-report
```

Opens an HTML report with:
- ✅ Test results (pass/fail)
- 📸 Screenshots (on failure)
- 🎥 Videos (on failure)
- 📝 Execution traces
- ⏱️ Timing information

## 🌐 Browser Coverage

Tests run on:
- **Chrome/Edge** (Chromium)
- **Firefox**
- **Safari** (WebKit)
- **Mobile Chrome** (Pixel 5)
- **Mobile Safari** (iPhone 12)

## 📁 Test Files

Located in `tests/e2e/`:

| File | What It Tests |
|------|---------------|
| `01-setup.spec.ts` | Initial load, theme, setup page |
| `02-player-management.spec.ts` | Adding/removing players |
| `03-session-start.spec.ts` | Starting sessions, all modes |
| `04-match-management.spec.ts` | Match operations, scores |
| `05-rankings-stats.spec.ts` | Rankings/stats modals |
| `06-local-storage.spec.ts` | Data persistence |
| `07-locked-teams.spec.ts` | Team management |

## 💡 Common Commands

```bash
# Run specific test file
npx playwright test tests/e2e/01-setup.spec.ts

# Run specific test
npx playwright test -g "should load the application"

# Run on specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox

# Run with UI and debug
npm run test:e2e:ui

# Show last test report
npx playwright show-report
```

## 🐛 Debugging Tips

1. **Use UI Mode** - Best for developing/debugging tests
   ```bash
   npm run test:e2e:ui
   ```

2. **Use Debug Mode** - Step through tests
   ```bash
   npm run test:e2e:debug
   ```

3. **View Trace** - See what happened
   ```bash
   npx playwright show-trace trace.zip
   ```

4. **Check Screenshots** - Auto-captured on failure in `playwright-report/`

## ✍️ Writing Tests

Example test structure:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await page.fill('#input', 'value');
    
    // Act
    await page.click('#button');
    
    // Assert
    await expect(page.locator('#result')).toBeVisible();
  });
});
```

## 📈 Test Coverage

Current: **70+ tests** covering major workflows

Tests include:
- Happy paths (expected user flows)
- Edge cases (validation, empty states)
- Persistence (localStorage, page refresh)
- UI interactions (modals, forms, buttons)
- Multi-step workflows (complete sessions)

## 🔧 Configuration

Edit `playwright.config.ts` to customize:
- Browsers to test
- Timeout values
- Screenshot/video options
- Base URL
- Test directory

## 🎯 CI/CD Integration

Tests are ready for CI/CD:

```bash
# Run in CI mode
CI=true npm run test:e2e
```

Features:
- Automatic retries (2x on failure)
- HTML reports
- Screenshots and videos
- No parallel execution (stability)

## 🆘 Troubleshooting

### Error: Cannot find browser

```bash
npx playwright install --force
```

### Port 5173 already in use

Kill the process using that port, then try again.

### Tests timing out

Check `playwright.config.ts` and increase timeout if needed.

### Flaky tests

- Tests are designed to be stable
- If flaky, check for race conditions
- Use `waitForSelector` for dynamic content

## 📚 Learn More

- Full documentation: `tests/README.md`
- [Playwright Docs](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)

## 🎉 Benefits

✅ **Catch bugs early** - Before users find them
✅ **Regression prevention** - Ensure changes don't break features
✅ **Documentation** - Tests show how features work
✅ **Confidence** - Deploy with certainty
✅ **Multi-browser** - Works everywhere
✅ **Real browser** - Tests actual user experience

## Next Steps

1. **Run the tests** - See everything in action
2. **Explore UI mode** - Interactive testing experience
3. **Add your tests** - Cover new features
4. **Integrate with CI** - Automate testing

Happy Testing! 🧪🎾
