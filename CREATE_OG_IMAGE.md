# How to Create Your Social Media Preview Image (og-image.png)

## Quick Start

Create an image file named `og-image.png` in the `public` folder with these specifications:

## Image Specifications

- **Dimensions**: 1200 x 630 pixels (required for optimal display)
- **Format**: PNG or JPG (PNG recommended)
- **File size**: Under 8MB (ideally under 500KB)
- **Location**: `public/og-image.png`

## Design Guidelines

### What to Include:

1. **App Name**: "Better Pickleball Sessions" in large text
2. **Tagline**: "Professional Session Management" 
3. **Visual Element**: 
   - Pickleball icon/emoji 🎾
   - Screenshot of the app
   - Court illustration
   - Clean gradient background

4. **Key Features** (optional):
   - "Smart Matchmaking"
   - "Round Robin & King of Court"
   - "Real-time Rankings"

### Design Tips:

- Use high contrast text for readability
- Keep important content in the center (safe zone: 1200x600)
- Use your app's color scheme (purple/blue gradient)
- Make text readable at small sizes (mobile preview)
- Test on both light and dark backgrounds

## Easy Creation Methods

### Option 1: Canva (Easiest - Free)

1. Go to https://www.canva.com
2. Create design → Custom size → 1200 x 630 px
3. Use template: "Facebook Post" or "Twitter Post"
4. Add:
   - Background: Gradient (#667eea to #764ba2)
   - Text: "Better Pickleball Sessions"
   - Subtitle: "Professional Session Management"
   - Icon: 🎾 or search "pickleball"
5. Download as PNG
6. Save to `public/og-image.png`

### Option 2: Figma (Professional - Free)

1. Create new file at 1200x630px
2. Add gradient background
3. Add text layers with app name and features
4. Export as PNG 2x
5. Save to `public/og-image.png`

### Option 3: Screenshot + Text Editor

1. Take a screenshot of your app
2. Use any image editor (Paint, Photoshop, GIMP, Pixlr)
3. Create canvas: 1200x630
4. Add screenshot (scaled to fit)
5. Add text overlay with app name
6. Export as PNG
7. Save to `public/og-image.png`

### Option 4: Online Tools

**Placid.app**: https://placid.app/
- Free social media image generator
- Templates available

**Meta Tags**: https://metatags.io/
- Preview and generate OG images
- See how it looks on different platforms

**Social Image Generator**: https://www.socialimage.io/
- Simple, free tool
- No design skills needed

## Quick Placeholder

If you need a temporary image, use this simple approach:

1. Create a 1200x630 image with:
   - Solid gradient background
   - Center text: "Better Pickleball Sessions"
   - Emoji: 🎾
   - White text, large font (80-100px)

2. Or use an online text-to-image generator:
   - https://www.brandcrowd.com/
   - https://www.canva.com/design/play

## Example Layout

```
┌─────────────────────────────────────────────┐
│                                             │
│            🎾 Better Pickleball             │
│                  Sessions                    │
│                                             │
│      Professional Session Management        │
│                                             │
│    ✓ Smart Matchmaking  ✓ Live Rankings    │
│    ✓ Round Robin        ✓ King of Court    │
│                                             │
│         [Optional: App Screenshot]          │
│                                             │
└─────────────────────────────────────────────┘
     1200px x 630px
```

## Testing Your Image

After creating the image:

1. **Facebook Debugger**: 
   - https://developers.facebook.com/tools/debug/
   - Enter: https://betterpickleballsessions.com
   - Click "Scrape Again" to refresh cache

2. **Twitter Card Validator**:
   - https://cards-dev.twitter.com/validator
   - Enter your URL
   - See how card looks

3. **LinkedIn Post Inspector**:
   - https://www.linkedin.com/post-inspector/
   - Check LinkedIn preview

4. **Browser Preview**:
   - Share URL in Slack/Discord/iMessage
   - Verify image appears correctly

## Color Palette (from your app)

- **Gradient Start**: #667eea (blue-purple)
- **Gradient End**: #764ba2 (purple)
- **White**: #ffffff (for text)
- **Dark**: #0d1117 (for dark mode backgrounds)

## Font Suggestions

- **Primary**: Segoe UI, Inter, Roboto
- **Backup**: Arial, Helvetica, sans-serif
- **Weight**: 600-700 (semi-bold to bold)

## After Creating the Image

1. Save as `og-image.png` in the `public` folder
2. Run `npm run build` to rebuild
3. Deploy to GitHub Pages
4. Test with Facebook Debugger and Twitter Validator
5. Clear any social media caches if image doesn't show

## Pro Tips

- Use tools like **Squoosh.app** to compress image if needed
- Keep file size under 500KB for faster loading
- Test on mobile - preview at small sizes
- Consider creating variations for different platforms
- Update the image when you make major feature updates

## Alternative: Use Text-Only

If you don't want to create an image, you can remove the og:image tags and social platforms will generate a text-only preview using your title and description (which are already optimized).

To do this, remove these lines from `index.html`:
```html
<meta property="og:image" content="https://betterpickleballsessions.com/og-image.png">
<meta property="twitter:image" content="https://betterpickleballsessions.com/og-image.png">
```

The site will still work fine - you just won't have a visual preview on social media.
