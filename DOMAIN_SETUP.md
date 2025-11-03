# 🌐 BetterPickleballSessions.com - Domain Setup Guide

## Domain Configuration Complete! ✅

Your app is now configured for **BetterPickleballSessions.com**

---

## Changes Made

### 1. ✅ Updated Application Name
- **App Title**: "Better Pickleball Sessions"
- **Subtitle**: "Professional session management made easy"
- **Package Name**: `better-pickleball-sessions`
- **Homepage**: https://betterpickleballsessions.com

### 2. ✅ Updated Vite Configuration
```typescript
export default {
  base: '/',  // Changed from '/pickleball/' to '/'
  publicDir: 'public',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
};
```

### 3. ✅ Created CNAME File
Location: `public/CNAME`
```
betterpickleballsessions.com
```

### 4. ✅ Added Navigation System
- **Setup** - Initial session configuration
- **Active Session** - Live session management
- **Modes & Config** - Detailed documentation of game modes
- **About** - Information about the app and features

### 5. ✅ Created New Pages
- **Modes & Config Page**: Explains Round Robin and King of the Court modes
- **About Page**: Features, getting started guide, and app information

---

## DNS Configuration Required

You need to configure your domain's DNS settings with your domain registrar.

### Option 1: GitHub Pages (Recommended)

**If deploying to GitHub Pages:**

1. Go to your domain registrar (where you bought BetterPickleballSessions.com)
2. Add these DNS records:

   **For apex domain (betterpickleballsessions.com):**
   ```
   Type: A
   Name: @
   Value: 185.199.108.153
   
   Type: A
   Name: @
   Value: 185.199.109.153
   
   Type: A
   Name: @
   Value: 185.199.110.153
   
   Type: A
   Name: @
   Value: 185.199.111.153
   ```

   **For www subdomain:**
   ```
   Type: CNAME
   Name: www
   Value: <your-github-username>.github.io
   ```

3. Wait for DNS propagation (can take 24-48 hours)

### Option 2: Custom Hosting

If using a different hosting provider, follow their DNS configuration instructions.

---

## Deployment Steps

### 1. Build the Application
```bash
npm run build
```

This creates a production build in the `dist/` folder with:
- Optimized JavaScript/CSS
- CNAME file for custom domain
- All assets

### 2. Deploy to GitHub Pages

```bash
npm run deploy
```

This will:
- Build the application
- Push to `gh-pages` branch
- Make it available at your GitHub Pages URL

### 3. Configure GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Pages**
3. Under "Custom domain", enter: `betterpickleballsessions.com`
4. Check "Enforce HTTPS" (after DNS propagates)
5. Save

### 4. Wait for DNS Propagation

- DNS changes can take 24-48 hours
- Check status: https://www.whatsmydns.net/#A/betterpickleballsessions.com
- Once propagated, your site will be live!

---

## Verify Deployment

After DNS propagates, verify your site works:

1. **Visit**: https://betterpickleballsessions.com
2. **Check Navigation**: Click through all 4 tabs
3. **Test Features**: 
   - Add players
   - Start a session
   - Complete a match
   - View rankings

---

## Navigation Structure

### Setup Tab
- Game mode selection (Round Robin / King of Court)
- Session type (Doubles / Singles)
- Number of courts
- Player management
- Advanced configuration

### Active Session Tab
- Live court display
- Match management
- Player controls
- Session controls (queue, history, rankings, etc.)

### Modes & Config Tab
- **Round Robin Mode**: Detailed explanation
- **King of the Court Mode**: Detailed explanation
- **Configuration Options**: All settings explained
- **Tips**: Best practices

### About Tab
- Welcome message
- Key features (8 feature cards)
- Getting started guide
- Use cases
- Technology stack
- Call-to-action button

---

## Local Development

Test locally before deploying:

```bash
# Start dev server
npm run dev

# Visit
http://localhost:5173
```

The app will work exactly as it will on the live domain.

---

## Important Files

- `vite.config.ts` - Build configuration with base URL set to `/`
- `public/CNAME` - Custom domain file (auto-copied to dist)
- `package.json` - Package configuration with homepage URL
- `index.html` - Main HTML with navigation and new pages
- `src/main.ts` - Application logic with navigation handlers

---

## Post-Deployment Checklist

- [ ] DNS A records added to domain registrar
- [ ] DNS CNAME record for www subdomain added
- [ ] `npm run build` completes successfully
- [ ] `npm run deploy` pushes to gh-pages branch
- [ ] GitHub Pages custom domain configured
- [ ] HTTPS enabled in GitHub Pages settings
- [ ] DNS propagation complete (check whatsmydns.net)
- [ ] Site loads at https://betterpickleballsessions.com
- [ ] All navigation tabs work
- [ ] Test session functionality works
- [ ] Mobile responsive design works

---

## Common Issues & Solutions

### Issue: Site shows 404
**Solution**: 
- Check GitHub Pages settings
- Verify CNAME file exists in dist folder
- Wait for DNS propagation

### Issue: CSS/JS not loading
**Solution**:
- Verify `base: '/'` in vite.config.ts
- Rebuild: `npm run build`
- Redeploy: `npm run deploy`

### Issue: Domain not resolving
**Solution**:
- Check DNS records are correct
- Use whatsmydns.net to check propagation
- Wait up to 48 hours for full propagation

### Issue: HTTPS not working
**Solution**:
- Wait for DNS propagation first
- Enable "Enforce HTTPS" in GitHub Pages settings
- Wait a few minutes for certificate generation

---

## Features Added

✅ **Single Page App Navigation**
- Smooth transitions between pages
- Active tab highlighting
- No page refreshes

✅ **Modes & Config Page**
- Complete documentation of both game modes
- All configuration options explained
- Best practices and tips

✅ **About Page**
- Professional welcome message
- 8 feature highlight cards
- Getting started guide
- Use cases and technology info
- Call-to-action button to start

✅ **Professional Branding**
- "Better Pickleball Sessions" title
- Clean navigation bar
- Consistent styling
- Mobile responsive

---

## Next Steps

1. **Build & Deploy**
   ```bash
   npm run build
   npm run deploy
   ```

2. **Configure DNS**
   - Add A records to domain registrar
   - Add www CNAME record

3. **Set GitHub Pages Custom Domain**
   - Repository Settings → Pages
   - Enter: betterpickleballsessions.com

4. **Wait for Propagation**
   - Check whatsmydns.net
   - Can take up to 48 hours

5. **Enable HTTPS**
   - In GitHub Pages settings
   - After DNS propagates

6. **Test Everything**
   - Visit live site
   - Test all features
   - Check on mobile

---

## Success! 🎉

Your Better Pickleball Sessions app is now:
- ✅ Professionally branded
- ✅ Configured for custom domain
- ✅ Enhanced with navigation
- ✅ Documented with new pages
- ✅ Ready for deployment

Visit **https://betterpickleballsessions.com** after DNS propagation! 🎾
