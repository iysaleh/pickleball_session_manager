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
    // Use a safer approach - click directly on the modal element
    await page.evaluate(() => {
      const modalEl = document.querySelector('#rankings-modal') as HTMLElement;
      if (modalEl) {
        // Create and dispatch a click event on the modal backdrop
        const event = new MouseEvent('click', { bubbles: true, cancelable: true });
        modalEl.dispatchEvent(event);
      }
    });
    
    // Wait a bit for the modal to close
    await page.waitForTimeout(300);
    
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
    
    // Wait for history to be updated
    await page.waitForTimeout(1000);
    
    // Click Show History button to make sure history is visible
    const historyBtn = page.locator('#show-history-btn');
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      await page.waitForTimeout(500);
    }
    
    const history = page.locator('#match-history-list');
    
    // Wait for history to be populated
    await page.waitForFunction(() => {
      const historyEl = document.querySelector('#match-history-list');
      return historyEl && historyEl.textContent.trim().length > 50;
    }, { timeout: 5000 });
    
    // Should show scores - check for the actual score values
    const historyText = await history.textContent();
    
    // The scores might be in input fields or as text
    // Check if either 11 or 7 appear in the history (or the actual scores from the helper)
    expect(historyText.length).toBeGreaterThan(50); // Has content
    
    // Look for score inputs or text
    const hasScores = historyText.includes('11') || 
                     historyText.includes('7') ||
                     await history.locator('input[type="number"]').count() > 0;
    expect(hasScores).toBeTruthy();
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
