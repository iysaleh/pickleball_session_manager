# GitHub Pages Deployment Guide 🚀

This Pickleball Session Manager is a **purely client-side application** with no server requirements. All data is stored locally in the browser using localStorage. This makes it perfect for GitHub Pages!

## Prerequisites

- A GitHub account
- Git installed on your computer
- Node.js and npm installed

## Initial Setup

### 1. Create GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `pickleball` (or any name you prefer)
3. Make it public (required for free GitHub Pages)
4. Don't initialize with README (since you already have a project)

### 2. Configure Vite Base Path

In `vite.config.ts`, update the `base` property to match your repository name:

```typescript
export default defineConfig({
  base: '/pickleball/', // Change 'pickleball' to your repo name
  // ...
});
```

**Important:** If your repo name is different, replace `pickleball` with your actual repo name.

### 3. Connect Local Repository to GitHub

Open terminal/command prompt in your project directory and run:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Pickleball Session Manager"

# Add remote (replace YOUR-USERNAME and YOUR-REPO-NAME)
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 4. Install Dependencies

```bash
npm install
```

This will install the `gh-pages` package needed for deployment.

## Deploying to GitHub Pages

### Option 1: Using npm script (Recommended)

Simply run:

```bash
npm run deploy
```

This will:
1. Build the production version (`npm run build`)
2. Deploy to GitHub Pages (`gh-pages -d dist`)

### Option 2: Manual GitHub Actions (Alternative)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Build
        run: npm run build
        
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './dist'
          
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

Then enable GitHub Pages in your repository settings to use GitHub Actions.

## Accessing Your Deployed Site

After deployment, your site will be available at:

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/
```

For example: `https://yourusername.github.io/pickleball/`

## Updating the Site

To update the site after making changes:

```bash
# Make your changes, then:
git add .
git commit -m "Description of changes"
git push origin main

# Deploy the updates
npm run deploy
```

## Important Notes

### ✅ **No Server Required**
- This is a 100% client-side application
- All data is stored in the browser's localStorage
- No backend, database, or server needed
- Free to host on GitHub Pages

### 🔒 **Data Persistence**
- Each user's data is stored locally on their device
- Data persists across page refreshes
- Data is private to each user's browser
- Clearing browser data will clear session data

### 📱 **Features That Work**
- ✅ All session management
- ✅ Player/team tracking
- ✅ Match management
- ✅ Rankings and statistics
- ✅ Data persistence (localStorage)
- ✅ All UI features

### 🌐 **Cross-Browser Compatibility**
Works on all modern browsers:
- Chrome, Edge, Firefox, Safari
- Mobile browsers (iOS Safari, Chrome Mobile)

### 💾 **Data Storage**
- Uses browser's localStorage API
- Approximately 5-10MB storage limit per domain
- More than enough for hundreds of sessions

## Troubleshooting

### Issue: Site shows blank page or 404
**Solution:** Make sure the `base` in `vite.config.ts` matches your repo name exactly, including the leading and trailing slashes.

### Issue: Assets not loading
**Solution:** Clear browser cache and hard refresh (Ctrl+F5 or Cmd+Shift+R)

### Issue: Deployment fails
**Solution:** 
1. Ensure you have pushed all changes to GitHub
2. Run `npm install` to ensure all dependencies are installed
3. Try running `npm run build` locally first to catch any build errors

### Issue: Old version showing after deployment
**Solution:** 
1. Clear browser cache
2. GitHub Pages can take a few minutes to update
3. Try accessing in incognito/private mode

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file to the `public` directory with your domain
2. Configure DNS settings at your domain registrar
3. Enable custom domain in GitHub repository settings

## Repository Settings for GitHub Pages

After first deployment:

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Source", select `gh-pages` branch
4. Click Save

The site will be live in a few minutes!

## Development vs Production

### Development (Local)
```bash
npm run dev
```
Access at: `http://localhost:5173`

### Production (GitHub Pages)
```bash
npm run deploy
```
Access at: `https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

## Questions?

This is a standard static site deployment. No special configuration needed beyond what's described here!
