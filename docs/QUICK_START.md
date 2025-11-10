# 🚀 Quick Start - Deploy to GitHub Pages

## TL;DR - 5 Steps to Deploy

```bash
# 1. Update vite.config.ts with your repo name
# Change: base: '/pickleball/' to base: '/YOUR-REPO-NAME/'

# 2. Install dependencies
npm install

# 3. Initialize git and push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
git push -u origin main

# 4. Deploy to GitHub Pages
npm run deploy

# 5. Enable GitHub Pages (first time only)
# Go to: GitHub repo → Settings → Pages
# Source: Deploy from a branch
# Branch: gh-pages → / (root) → Save
```

Your site will be live at: `https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

## Important: Update Repository Name

Before deploying, you **must** update the base path in `vite.config.ts`:

```typescript
export default defineConfig({
  base: '/YOUR-ACTUAL-REPO-NAME/', // ← Change this!
  // ...
});
```

## Updating After Changes

```bash
git add .
git commit -m "Your change description"
git push origin main
npm run deploy
```

## Need Help?

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions and troubleshooting.

## What Gets Deployed?

- ✅ All HTML, CSS, JavaScript files
- ✅ Compiled TypeScript
- ✅ Optimized and minified code
- ✅ All assets and images

## What Doesn't Get Deployed?

- ❌ node_modules/
- ❌ Source TypeScript files (.ts)
- ❌ Development files
- ❌ Tests

## Why GitHub Pages?

- ✅ **Free** - No cost
- ✅ **No Server** - This is a client-side app
- ✅ **Fast** - CDN-backed
- ✅ **Reliable** - GitHub's infrastructure
- ✅ **HTTPS** - Secure by default
- ✅ **Easy** - One command deployment

## Data Storage

All session data is stored in each user's browser using localStorage:
- ✅ Private to each user
- ✅ Persists across page refreshes
- ✅ No database needed
- ✅ No backend required
- ✅ Works offline after first load

## Browser Support

Works on all modern browsers:
- ✅ Chrome/Edge (Desktop & Mobile)
- ✅ Firefox (Desktop & Mobile)
- ✅ Safari (Desktop & Mobile)
- ✅ Any browser supporting ES6+ and localStorage

Enjoy your Pickleball Session Manager! 🎾
