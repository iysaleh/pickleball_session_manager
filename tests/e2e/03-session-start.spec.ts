import { test, expect } from '@playwright/test';

test.describe('Session Start', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  const addPlayers = async (page: any, count: number = 8) => {
    for (let i = 1; i <= count; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
  };

  test('should start a doubles round-robin session', async ({ page }) => {
    await page.goto('/');
    
    // Add players
    await addPlayers(page, 8);
    
    // Select round-robin
    await page.selectOption('#game-mode', 'round-robin');
    await page.selectOption('#session-type', 'doubles');
    
    // Start session
    await page.click('#start-session-btn');
    
    // Setup section should be hidden
    await expect(page.locator('#setup-section')).toBeHidden();
    
    // Control section should be visible
    await expect(page.locator('#control-section')).toBeVisible();
    
    // Courts section should be visible
    await expect(page.locator('#courts-section')).toBeVisible();
  });

  test('should start a singles session', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 4);
    
    await page.selectOption('#game-mode', 'round-robin');
    await page.selectOption('#session-type', 'singles');
    
    await page.click('#start-session-btn');
    
    await expect(page.locator('#control-section')).toBeVisible();
  });

  test('should start king-of-court session', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 8);
    
    await page.selectOption('#game-mode', 'king-of-court');
    
    await page.click('#start-session-btn');
    
    await expect(page.locator('#control-section')).toBeVisible();
    
    // Start next round button should be visible for king-of-court
    await expect(page.locator('#start-next-round-btn')).toBeVisible();
  });

  test('should display active courts after session start', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 8);
    
    await page.click('#start-session-btn');
    
    // Should show courts
    const courts = page.locator('.court');
    const courtCount = await courts.count();
    expect(courtCount).toBeGreaterThan(0);
  });

  test('should auto-start matches', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 8);
    
    await page.click('#start-session-btn');
    
    // Wait for courts to load
    await page.waitForSelector('.court', { timeout: 5000 });
    
    // Check for in-progress matches
    const inProgressStatus = page.locator('.status-in-progress');
    const count = await inProgressStatus.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display session controls', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 6);
    
    await page.click('#start-session-btn');
    
    // Check all control buttons are present
    await expect(page.locator('#show-queue-btn')).toBeVisible();
    await expect(page.locator('#show-history-btn')).toBeVisible();
    await expect(page.locator('#show-rankings-btn')).toBeVisible();
    await expect(page.locator('#show-stats-btn')).toBeVisible();
    await expect(page.locator('#edit-session-btn')).toBeVisible();
    await expect(page.locator('#clear-session-btn')).toBeVisible();
    await expect(page.locator('#end-session-btn')).toBeVisible();
  });

  test('should display active players list', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 6);
    
    await page.click('#start-session-btn');
    
    const activePlayersList = page.locator('#active-players-list');
    await expect(activePlayersList).toBeVisible();
    
    // Should contain player names
    for (let i = 1; i <= 6; i++) {
      await expect(activePlayersList).toContainText(`Player ${i}`);
    }
  });

  test('should set correct number of courts', async ({ page }) => {
    await page.goto('/');
    
    await addPlayers(page, 8);
    
    // Set to 2 courts
    await page.fill('#num-courts', '2');
    
    await page.click('#start-session-btn');
    
    // Count court elements
    const courts = page.locator('.court');
    await expect(courts).toHaveCount(2);
  });
});
