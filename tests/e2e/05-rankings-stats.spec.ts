import { test, expect } from '@playwright/test';

test.describe('Rankings and Statistics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  const startSessionAndCompleteMatch = async (page: any) => {
    // Add players
    for (let i = 1; i <= 8; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
    }
    
    await page.click('#start-session-btn');
    await page.waitForSelector('.status-in-progress', { timeout: 5000 });
    
    // Complete a match
    const firstMatch = page.locator('.court').first();
    await firstMatch.locator('input[id^="score1-"]').fill('11');
    await firstMatch.locator('input[id^="score2-"]').fill('7');
    await firstMatch.locator('button:has-text("Complete")').click();
    
    await page.waitForTimeout(1000);
  };

  test('should open rankings modal', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    // Click show rankings
    await page.click('#show-rankings-btn');
    
    // Modal should be visible
    const modal = page.locator('#rankings-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Should have header
    await expect(modal.locator('.modal-header')).toContainText('Rankings');
  });

  test('should close rankings modal', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-rankings-btn');
    
    // Modal is open
    const modal = page.locator('#rankings-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Click close button
    await page.click('#rankings-modal-close');
    
    // Modal should be closed
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should close rankings modal by clicking backdrop', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-rankings-btn');
    
    const modal = page.locator('#rankings-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Click on modal backdrop (the modal itself, not the content)
    await modal.click({ position: { x: 10, y: 10 } });
    
    // Modal should be closed
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should display rankings with player names', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-rankings-btn');
    
    // Should show rankings
    const rankingsList = page.locator('#rankings-list');
    const rankings = rankingsList.locator('.ranking-item');
    
    expect(await rankings.count()).toBeGreaterThan(0);
    
    // Should show player names
    await expect(rankingsList).toContainText('Player');
  });

  test('should show wins and losses in rankings', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-rankings-btn');
    
    const rankingsList = page.locator('#rankings-list');
    
    // Should show Wins and Losses labels
    await expect(rankingsList).toContainText('Wins');
    await expect(rankingsList).toContainText('Losses');
  });

  test('should open statistics modal', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-stats-btn');
    
    const modal = page.locator('#stats-modal');
    await expect(modal).toHaveClass(/show/);
    
    await expect(modal.locator('.modal-header')).toContainText('Statistics');
  });

  test('should close statistics modal', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-stats-btn');
    
    const modal = page.locator('#stats-modal');
    await expect(modal).toHaveClass(/show/);
    
    await page.click('#stats-modal-close');
    
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should display player statistics', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    await page.click('#show-stats-btn');
    
    const statsGrid = page.locator('#stats-grid');
    const statCards = statsGrid.locator('.stat-card');
    
    expect(await statCards.count()).toBeGreaterThan(0);
  });

  test('should show match history', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    // History should be visible by default
    const history = page.locator('#match-history-list');
    await expect(history).toBeVisible();
    
    // Should have at least one match
    const cards = history.locator('.history-card');
    expect(await cards.count()).toBeGreaterThan(0);
  });

  test('should toggle match history', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    const historySection = page.locator('#match-history-section');
    const historyBtn = page.locator('#show-history-btn');
    
    // Initially visible
    await expect(historySection).toBeVisible();
    await expect(historyBtn).toContainText('Hide');
    
    // Click to hide
    await page.click('#show-history-btn');
    await expect(historySection).toBeHidden();
    await expect(historyBtn).toContainText('Show');
    
    // Click to show again
    await page.click('#show-history-btn');
    await expect(historySection).toBeVisible();
  });

  test('should display match scores in history', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    const history = page.locator('#match-history-list');
    
    // Should show score
    await expect(history).toContainText('11');
    await expect(history).toContainText('7');
  });

  test('should prevent body scroll when modal is open', async ({ page }) => {
    await page.goto('/');
    await startSessionAndCompleteMatch(page);
    
    // Check body overflow before opening modal
    const bodyBefore = await page.evaluate(() => document.body.style.overflow);
    expect(bodyBefore).toBe('');
    
    // Open modal
    await page.click('#show-rankings-btn');
    
    // Body should have overflow hidden
    const bodyAfter = await page.evaluate(() => document.body.style.overflow);
    expect(bodyAfter).toBe('hidden');
    
    // Close modal
    await page.click('#rankings-modal-close');
    
    // Body should be restored
    const bodyRestored = await page.evaluate(() => document.body.style.overflow);
    expect(bodyRestored).toBe('');
  });
});
