# 🚀 Quick Reference Card

## Essential Commands

### Development
```bash
# Start dev server
npx -y vite@latest

# Start dev server (if npm works)
npm run dev
```

### Testing

#### Run All Tests
```bash
npm run test:all          # Complete test suite
node run-all-tests.js     # Same as above
run-tests.bat             # Windows batch
.\run-tests.ps1           # Windows PowerShell
```

#### E2E Tests Only
```bash
npx playwright test       # All browsers, headless
npm run test:e2e:ui       # Interactive UI mode
npm run test:e2e:headed   # Visible browsers
npm run test:e2e:debug    # Debug mode
```

#### Unit Tests Only
```bash
npm test                  # Watch mode
npm run test:run          # Run once
npm run test:ui           # Interactive UI
```

#### Check Configuration
```bash
node check-config.js      # Validate setup
```

### Building & Deployment
```bash
npm run build             # Build for production
npm run deploy            # Deploy to GitHub Pages
npm run preview           # Preview production build
```

### View Reports
```bash
npx playwright show-report    # E2E test report
```

## File Structure

```
pickleball/
├── src/                      # Source code
│   └── main.ts              # Main application
├── tests/
│   └── e2e/                 # E2E tests (Playwright)
│       ├── 00-dev-server.spec.ts
│       ├── 01-setup.spec.ts
│       ├── 02-player-management.spec.ts
│       ├── 03-session-start.spec.ts
│       ├── 04-match-management.spec.ts
│       ├── 05-rankings-stats.spec.ts
│       ├── 06-local-storage.spec.ts
│       └── 07-locked-teams.spec.ts
├── index.html               # Entry point
├── vite.config.ts           # Vite configuration
├── playwright.config.ts     # Playwright configuration
├── package.json             # Dependencies & scripts
├── run-all-tests.js         # Test runner
├── check-config.js          # Config validator
├── run-tests.bat            # Windows batch script
└── run-tests.ps1            # PowerShell script
```

## URLs

- **Local Dev**: http://localhost:5173/pickleball/
- **GitHub Pages**: https://username.github.io/pickleball/

## Test Coverage

✅ **70+ E2E Tests** covering:
- Application setup
- Player management
- Session creation (Round Robin, King of Court)
- Match operations
- Rankings & statistics
- Data persistence
- Locked teams
- UI interactions

✅ **5 Browsers**:
- Desktop: Chrome, Firefox, Safari
- Mobile: Chrome, Safari

## Quick Fixes

### Port 5173 in use
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Tests failing
```bash
# Install Playwright browsers
npx playwright install

# Run with UI to debug
npm run test:e2e:ui
```

### Config errors
```bash
# Validate configuration
node check-config.js
```

### npm install broken
```bash
# Use npx to run vite directly
npx -y vite@latest
```

## Exit Codes

- `0` = Success ✅
- `1` = Failure ❌

## Color Legend (Terminal)

- 🟢 Green = Passed
- 🔴 Red = Failed
- 🟡 Yellow = Warning/Skipped
- 🔵 Blue = Info
- 🟣 Magenta = Title

## Common Issues

| Issue | Solution |
|-------|----------|
| Server won't start | Use `npx -y vite@latest` |
| Tests timeout | Increase timeouts in playwright.config.ts |
| npm install fails | Already handled - tests use npx |
| Port in use | Kill process or let config reuse |

## Test Duration

- Config Check: ~1s
- E2E Tests: ~3-4min
- Unit Tests: ~10-30s
- **Total**: ~4-5min

## Pre-Commit Checklist

- [ ] Run all tests: `npm run test:all`
- [ ] All tests pass
- [ ] Check git status: `git status`
- [ ] Commit: `git commit -m "message"`

## Pre-Deploy Checklist

- [ ] Run all tests: `npm run test:all`
- [ ] Build: `npm run build`
- [ ] Preview: `npm run preview`
- [ ] Deploy: `npm run deploy`

## Support

- **Test Runner Guide**: TEST_RUNNER_GUIDE.md
- **Testing Guide**: TESTING.md
- **Deployment Guide**: DEPLOYMENT.md
- **Dev Server Guide**: DEV_SERVER_GUIDE.md

## Scripts Summary

| Script | Description |
|--------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Build for production |
| `npm run test:all` | Run all tests |
| `npm run test:e2e` | Run E2E tests |
| `npm run test:e2e:ui` | E2E with UI |
| `npm test` | Run unit tests |
| `npm run deploy` | Deploy to GitHub Pages |
| `node check-config.js` | Validate config |

## Get Started

1. **Start server**: `npx -y vite@latest`
2. **Run tests**: `npm run test:all`
3. **View app**: http://localhost:5173/pickleball/
4. **Deploy**: `npm run deploy`

---

**Keep this card handy!** Bookmark for quick reference. 📌
