# 🚀 Dev Server Guide

## Quick Start

### Option 1: Using npx (Recommended for this setup)

```bash
npx -y vite@latest
```

Then open: **http://localhost:5173/pickleball/**

### Option 2: Using npm script

```bash
npm run dev:npx
```

### Option 3: Using installed vite (requires npm install to work)

```bash
npm run dev
```

## Why the `/pickleball/` path?

The app is configured for GitHub Pages deployment with `base: '/pickleball/'` in vite.config.ts.

**For local development**, you can:

1. **Use the path as-is**: `http://localhost:5173/pickleball/`
2. **Or temporarily change it**: Edit vite.config.ts and change `base: '/pickleball/'` to `base: '/'`

## Configuration Check

Before starting the server, you can run a configuration check:

```bash
node check-config.js
```

This will verify:
- ✅ vite.config.ts is valid
- ✅ package.json is correct
- ✅ index.html exists
- ✅ src/main.ts exists
- ⚠️ node_modules status

## Common Issues

### Issue: "Cannot find package 'vite'"

**Cause**: vite.config.ts has `import { defineConfig } from 'vite'` but vite isn't installed

**Solution**: The vite.config.ts has been fixed to use plain exports instead:
```typescript
// ✅ Works without vite installed
export default {
  base: '/pickleball/',
  build: { ... }
};
```

### Issue: npm install doesn't work

**Cause**: npm environment configuration issue

**Solution**: Use npx to run vite directly:
```bash
npx -y vite@latest
```

### Issue: Page shows 404

**Cause**: Missing `/pickleball/` in URL

**Solution**: Make sure to navigate to `http://localhost:5173/pickleball/` (with trailing slash)

## Dev Server Test

A new test file has been added: `tests/e2e/00-dev-server.spec.ts`

This tests:
- ✅ Dev server starts
- ✅ App loads without errors
- ✅ CSS is applied
- ✅ JavaScript executes
- ✅ No console errors
- ✅ HMR (Hot Module Reload) works
- ✅ Module resolution works
- ✅ Config is valid

Run it with:
```bash
npm run test:e2e -- tests/e2e/00-dev-server.spec.ts
```

## Development Workflow

1. **Check configuration**:
   ```bash
   node check-config.js
   ```

2. **Start dev server**:
   ```bash
   npx -y vite@latest
   ```

3. **Open browser**:
   ```
   http://localhost:5173/pickleball/
   ```

4. **Make changes** - Vite will hot-reload automatically

5. **Stop server** - Press `Ctrl+C`

## For Production Deployment

The `base: '/pickleball/'` setting is perfect for GitHub Pages:

1. **Keep the setting as-is**
2. **Build**: `npm run build` (when npm is fixed)
3. **Deploy**: `npm run deploy` (when npm is fixed)

Your site will be at: `https://username.github.io/pickleball/`

## Server is Currently Running! ✅

The dev server should be running at:
- **Local**: http://localhost:5173/pickleball/
- **Port**: 5173

Press `Ctrl+C` to stop the server.

## Summary

- ✅ Dev server can run without npm install
- ✅ Use `npx -y vite@latest` to start
- ✅ Configuration is fixed (no problematic imports)
- ✅ Test added to catch config issues
- ✅ Check script available for validation

Happy developing! 🎾
