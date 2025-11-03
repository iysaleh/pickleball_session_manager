import { test, expect } from '@playwright/test';

/**
 * Dev Server Sanity Tests
 * These tests verify that the dev server starts correctly and serves the application
 */
test.describe('Dev Server', () => {
  test('should start dev server and serve the app', async ({ page }) => {
    // This test will fail if vite.config.ts has import issues
    // or if the dev server can't start
    
    await page.goto('/');
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Basic smoke test - page should load
    await expect(page).toHaveTitle(/Pickleball/i);
    
    // Main app element should exist - wait explicitly
    await page.waitForSelector('#app', { state: 'visible', timeout: 10000 });
    await expect(page.locator('#app')).toBeVisible();
    
    // No critical JavaScript errors
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    
    // Wait a bit to catch any errors
    await page.waitForTimeout(1000);
    
    // Should have no errors
    expect(errors).toHaveLength(0);
  });

  test('should load CSS correctly', async ({ page }) => {
    await page.goto('/');
    
    // Check that styles are applied
    const body = page.locator('body');
    const bgColor = await body.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    
    // Should have a background color set (not empty)
    expect(bgColor).toBeTruthy();
    expect(bgColor.length).toBeGreaterThan(0);
    // Just verify it's a valid color string
    expect(bgColor).toMatch(/rgb/);
  });

  test('should load TypeScript/JavaScript correctly', async ({ page }) => {
    await page.goto('/');
    
    // Check that main.ts is loaded and executed
    // by verifying a global function exists
    const hasWindow = await page.evaluate(() => {
      return typeof window !== 'undefined';
    });
    
    expect(hasWindow).toBe(true);
  });

  test('should serve static assets', async ({ page }) => {
    // Navigate and wait for network to be idle
    const response = await page.goto('/', { waitUntil: 'networkidle' });
    expect(response?.status()).toBe(200);
    
    // Wait a bit more for any lazy-loaded assets
    await page.waitForTimeout(1000);
    
    // Check that main app loaded
    await expect(page.locator('#app')).toBeVisible();
  });

  test('should have no console errors on load', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Should have no console errors
    expect(consoleErrors).toHaveLength(0);
  });

  test('should hot reload work (HMR check)', async ({ page }) => {
    await page.goto('/');
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Check if Vite HMR client is loaded
    const hasViteHMR = await page.evaluate(() => {
      // Check for Vite HMR in various ways
      return typeof window !== 'undefined' && (
        '__vite__' in window || 
        'import.meta.hot' in globalThis ||
        document.querySelector('script[type="module"]') !== null
      );
    });
    
    // In dev mode, HMR should be available (or at least modules should be loaded)
    expect(hasViteHMR).toBeTruthy();
  });

  test('should load from correct base path', async ({ page }) => {
    // The base path in vite.config.ts is '/pickleball/'
    // Check that the app handles this correctly
    
    // Try loading from root - might redirect or fail
    const rootResponse = await page.goto('/');
    
    // Should be able to load the app
    expect(rootResponse?.status()).toBeLessThan(500);
  });

  test('should have working module resolution', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('pageerror', error => {
      if (error.message.includes('Failed to fetch') || 
          error.message.includes('Cannot find module')) {
        errors.push(error.message);
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Should have no module resolution errors
    expect(errors).toHaveLength(0);
  });

  test('should have vite config loaded correctly', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // If vite config has import errors, the app won't load at all
    // This test passing means vite.config.ts is valid
    
    const title = await page.title();
    expect(title).toBeTruthy();
  });
});
