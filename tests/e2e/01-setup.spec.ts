import { test, expect } from '@playwright/test';

test.describe('Setup and Initial Load', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should load the application', async ({ page }) => {
    await page.goto('/');
    
    // Check for main heading
    await expect(page.locator('h1')).toContainText('Pickleball Session Manager');
    
    // Check for setup section
    await expect(page.locator('#setup-section')).toBeVisible();
  });

  test('should display theme toggle button', async ({ page }) => {
    await page.goto('/');
    
    const themeToggle = page.locator('#theme-toggle');
    await expect(themeToggle).toBeVisible();
    
    // Should show moon or sun emoji
    const text = await themeToggle.textContent();
    expect(text).toMatch(/[🌙☀️]/);
  });

  test('should toggle dark/light theme', async ({ page }) => {
    await page.goto('/');
    
    const html = page.locator('html');
    
    // Default is dark mode
    await expect(html).toHaveAttribute('data-theme', 'dark');
    
    // Click theme toggle
    await page.click('#theme-toggle');
    
    // Should switch to light mode (no data-theme attribute)
    await expect(html).not.toHaveAttribute('data-theme');
    
    // Click again
    await page.click('#theme-toggle');
    
    // Back to dark mode
    await expect(html).toHaveAttribute('data-theme', 'dark');
  });

  test('should have disabled start button initially', async ({ page }) => {
    await page.goto('/');
    
    const startBtn = page.locator('#start-session-btn');
    await expect(startBtn).toBeDisabled();
  });

  test('should display favicon', async ({ page }) => {
    await page.goto('/');
    
    const favicon = page.locator('link[rel="icon"]');
    const href = await favicon.getAttribute('href');
    
    // Check that favicon href exists and contains svg
    expect(href).toBeTruthy();
    expect(href).toContain('svg');
  });

  test('should have all game mode options', async ({ page }) => {
    await page.goto('/');
    
    const gameModeSelect = page.locator('#game-mode');
    await expect(gameModeSelect).toBeVisible();
    
    // Check for round-robin and king-of-court options
    const options = await gameModeSelect.locator('option').allTextContents();
    expect(options).toContain('Round Robin');
    expect(options).toContain('King of the Court');
  });

  test('should have session type options', async ({ page }) => {
    await page.goto('/');
    
    const sessionTypeSelect = page.locator('#session-type');
    await expect(sessionTypeSelect).toBeVisible();
    
    const options = await sessionTypeSelect.locator('option').allTextContents();
    expect(options).toContain('Doubles');
    expect(options).toContain('Singles');
  });

  test('should have default 4 courts', async ({ page }) => {
    await page.goto('/');
    
    const courtsInput = page.locator('#num-courts');
    await expect(courtsInput).toHaveValue('4');
  });
});
