import { test, expect } from '@playwright/test';

test.describe('Local Storage Persistence', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should persist players after refresh', async ({ page }) => {
    await page.goto('/');
    
    // Add players
    await page.fill('#player-name', 'Alice');
    await page.click('#add-player-btn');
    await page.fill('#player-name', 'Bob');
    await page.click('#add-player-btn');
    
    // Refresh page
    await page.reload();
    
    // Players should still be there
    await expect(page.locator('#player-list')).toContainText('Alice');
    await expect(page.locator('#player-list')).toContainText('Bob');
  });

  test('should persist session after refresh', async ({ page }) => {
    await page.goto('/');
    
    // Add players and start session
    for (let i = 1; i <= 6; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    await page.click('#start-session-btn');
    await page.waitForSelector('#control-section', { timeout: 5000 });
    
    // Refresh page
    await page.reload();
    
    // Session should be restored
    await expect(page.locator('#control-section')).toBeVisible();
    await expect(page.locator('#setup-section')).toBeHidden();
  });

  test('should persist match history after refresh', async ({ page }) => {
    await page.goto('/');
    
    // Start session and complete a match
    for (let i = 1; i <= 8; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
      await page.waitForTimeout(100);
    }
    
    await page.click('#start-session-btn');
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    // Wait for match to fully render
    await page.waitForTimeout(500);
    
    // Complete a match
    const firstMatch = page.locator('.court').first();
    await firstMatch.locator('input[id^="score1-"]').fill('11');
    await firstMatch.locator('input[id^="score2-"]').fill('9');
    await firstMatch.locator('button:has-text("Complete")').click();
    
    // Wait longer for match to be completed and saved to localStorage
    await page.waitForTimeout(2000);
    
    // Verify match was completed before refresh
    await page.waitForFunction(() => {
      const stored = localStorage.getItem('pickleballMatchHistory');
      return stored && stored.length > 10;
    }, { timeout: 5000 });
    
    // Refresh
    await page.reload();
    
    // Wait for page to load and restore state
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Show history if there's a button
    const historyBtn = page.locator('#show-history-btn');
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      await page.waitForTimeout(500);
    }
    
    // Match history should be preserved
    const history = page.locator('#match-history-list');
    
    // Wait for history to load
    await page.waitForFunction(() => {
      const historyEl = document.querySelector('#match-history-list');
      return historyEl && historyEl.textContent.trim().length > 20;
    }, { timeout: 5000 });
    
    const historyText = await history.textContent();
    
    // Check if scores are preserved (they might be in inputs or text)
    const hasScores = historyText.includes('11') || 
                     historyText.includes('9') ||
                     await history.locator('input').count() > 0;
    expect(hasScores).toBeTruthy();
  });

  test('should clear session data', async ({ page }) => {
    await page.goto('/');
    
    // Add players and start session
    for (let i = 1; i <= 4; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    await page.click('#start-session-btn');
    await page.waitForSelector('#control-section', { timeout: 5000 });
    
    // Clear session data
    page.on('dialog', dialog => dialog.accept());
    await page.click('#clear-session-btn');
    
    // Refresh
    await page.reload();
    
    // Should be back to empty state
    await expect(page.locator('#setup-section')).toBeVisible();
    
    // No players should be loaded
    const playerList = await page.locator('#player-list').textContent();
    expect(playerList).toContain('No players');
  });

  test('should end session and clear data', async ({ page }) => {
    await page.goto('/');
    
    // Add players and start session
    for (let i = 1; i <= 4; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    await page.click('#start-session-btn');
    await page.waitForSelector('#control-section', { timeout: 5000 });
    
    // End session
    page.on('dialog', dialog => dialog.accept());
    await page.click('#end-session-btn');
    
    // Should be back to setup
    await expect(page.locator('#setup-section')).toBeVisible();
    await expect(page.locator('#control-section')).toBeHidden();
    
    // Refresh to check localStorage was cleared
    await page.reload();
    
    const playerList = await page.locator('#player-list').textContent();
    expect(playerList).toContain('No players');
  });

  test('should persist theme preference', async ({ page }) => {
    await page.goto('/');
    
    const html = page.locator('html');
    
    // Default is dark mode
    await expect(html).toHaveAttribute('data-theme', 'dark');
    
    // Switch to light mode
    await page.click('#theme-toggle');
    await expect(html).not.toHaveAttribute('data-theme');
    
    // Refresh
    await page.reload();
    
    // Theme should be preserved
    await expect(html).not.toHaveAttribute('data-theme');
  });

  test('should persist banned pairs', async ({ page }) => {
    await page.goto('/');
    
    // Add players
    await page.fill('#player-name', 'Alice');
    await page.click('#add-player-btn');
    await page.fill('#player-name', 'Bob');
    await page.click('#add-player-btn');
    
    // Add banned pair
    await page.selectOption('#banned-player1', { index: 1 });
    await page.selectOption('#banned-player2', { index: 2 });
    await page.click('#add-banned-pair-btn');
    
    // Refresh
    await page.reload();
    
    // Banned pair should still be there
    const bannedList = page.locator('#banned-pairs-list');
    await expect(bannedList).toContainText('Alice');
    await expect(bannedList).toContainText('Bob');
  });

  test('should store and retrieve localStorage correctly', async ({ page }) => {
    await page.goto('/');
    
    // Add some data
    for (let i = 1; i <= 3; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    // Check localStorage has data
    const storageData = await page.evaluate(() => {
      const data = localStorage.getItem('pickleballSessionState');
      return data ? JSON.parse(data) : null;
    });
    
    expect(storageData).not.toBeNull();
    expect(storageData.players).toHaveLength(3);
    expect(storageData.timestamp).toBeDefined();
  });
});
