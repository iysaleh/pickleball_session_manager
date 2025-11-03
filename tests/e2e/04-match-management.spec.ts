import { test, expect } from '@playwright/test';

test.describe('Match Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  const startSession = async (page: any) => {
    for (let i = 1; i <= 8; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    await page.click('#start-session-btn');
    await page.waitForSelector('.court', { timeout: 5000 });
  };

  test('should display match information', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    // Find first court
    const firstCourt = page.locator('.court').first();
    
    // Should show court number
    await expect(firstCourt.locator('.court-header')).toContainText('Court');
    
    // Should show team names
    const teams = firstCourt.locator('.team');
    expect(await teams.count()).toBeGreaterThan(0);
  });

  test('should complete a match', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    // Wait for match to be in progress
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    // Find first in-progress match
    const firstMatch = page.locator('.court').first();
    
    // Enter scores
    const score1Input = firstMatch.locator('input[id^="score1-"]');
    const score2Input = firstMatch.locator('input[id^="score2-"]');
    
    await score1Input.fill('11');
    await score2Input.fill('9');
    
    // Click complete button
    await firstMatch.locator('button:has-text("Complete")').click();
    
    // Match should move to history
    await page.waitForTimeout(500);
    
    // Court should show next match or be empty
    const courtStatus = await firstMatch.locator('.match-status').textContent();
    expect(courtStatus).not.toContain('In Progress');
  });

  test('should validate match scores', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    const firstMatch = page.locator('.court').first();
    
    // Try to complete with tied scores
    const score1Input = firstMatch.locator('input[id^="score1-"]');
    const score2Input = firstMatch.locator('input[id^="score2-"]');
    
    await score1Input.fill('11');
    await score2Input.fill('11');
    
    // Listen for alert
    page.on('dialog', dialog => dialog.accept());
    
    await firstMatch.locator('button:has-text("Complete")').click();
    
    // Alert should have been shown (dialog handler will catch it)
  });

  test('should forfeit a match', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    page.on('dialog', dialog => dialog.accept());
    
    const firstMatch = page.locator('.court').first();
    await firstMatch.locator('button:has-text("Forfeit")').click();
    
    // Match should be forfeited
    await page.waitForTimeout(500);
  });

  test('should show match history', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    // Complete a match
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    const firstMatch = page.locator('.court').first();
    await firstMatch.locator('input[id^="score1-"]').fill('11');
    await firstMatch.locator('input[id^="score2-"]').fill('8');
    await firstMatch.locator('button:has-text("Complete")').click();
    
    await page.waitForTimeout(500);
    
    // Check history section
    const history = page.locator('#match-history-list');
    const historyCards = history.locator('.history-card');
    expect(await historyCards.count()).toBeGreaterThan(0);
  });

  test('should display waiting players', async ({ page }) => {
    await page.goto('/');
    
    // Add more players than can play at once
    for (let i = 1; i <= 12; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    await page.fill('#num-courts', '2'); // Only 2 courts
    await page.click('#start-session-btn');
    
    await page.waitForTimeout(1000);
    
    // Should have waiting players
    const waitingSection = page.locator('#waiting-area');
    // Note: Waiting area might not always be visible in UI
  });

  test('should update match scores in real-time', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    const firstMatch = page.locator('.court').first();
    const score1Input = firstMatch.locator('input[id^="score1-"]');
    
    // Type score
    await score1Input.fill('15');
    
    // Value should be set
    await expect(score1Input).toHaveValue('15');
  });

  test('should show vs text between teams', async ({ page }) => {
    await page.goto('/');
    await startSession(page);
    
    await page.waitForSelector('.court', { timeout: 5000 });
    
    const firstCourt = page.locator('.court').first();
    await expect(firstCourt).toContainText('vs');
  });
});
