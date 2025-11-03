import { test, expect } from '@playwright/test';

test.describe('Player Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should add a player', async ({ page }) => {
    await page.goto('/');
    
    // Add a player
    await page.fill('#player-name', 'John Doe');
    await page.click('#add-player-btn');
    
    // Check player appears in list
    await expect(page.locator('#player-list')).toContainText('John Doe');
    
    // Input should be cleared
    await expect(page.locator('#player-name')).toHaveValue('');
  });

  test('should add multiple players', async ({ page }) => {
    await page.goto('/');
    
    const players = ['Alice', 'Bob', 'Charlie', 'Diana'];
    
    for (const player of players) {
      await page.fill('#player-name', player);
      await page.click('#add-player-btn');
    }
    
    // All players should be visible
    for (const player of players) {
      await expect(page.locator('#player-list')).toContainText(player);
    }
  });

  test('should add player with Enter key', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('#player-name', 'Enter Test');
    await page.press('#player-name', 'Enter');
    
    await expect(page.locator('#player-list')).toContainText('Enter Test');
  });

  test('should enable start button after adding 2+ players', async ({ page }) => {
    await page.goto('/');
    
    const startBtn = page.locator('#start-session-btn');
    await expect(startBtn).toBeDisabled();
    
    // Add first player
    await page.fill('#player-name', 'Player 1');
    await page.click('#add-player-btn');
    await expect(startBtn).toBeDisabled();
    
    // Add second player
    await page.fill('#player-name', 'Player 2');
    await page.click('#add-player-btn');
    await expect(startBtn).toBeEnabled();
  });

  test('should remove a player', async ({ page }) => {
    await page.goto('/');
    
    // Add players
    await page.fill('#player-name', 'Alice');
    await page.click('#add-player-btn');
    await page.fill('#player-name', 'Bob');
    await page.click('#add-player-btn');
    
    // Wait for players to be added
    await page.waitForTimeout(500);
    
    // Find and click remove button for Alice
    const playerList = page.locator('#player-list');
    await expect(playerList).toContainText('Alice');
    
    // Click the first remove button more specifically
    await page.locator('#player-list ol li').first().locator('button').click();
    
    // Wait for removal
    await page.waitForTimeout(500);
    
    // Alice should be gone, Bob should remain
    const listText = await playerList.textContent();
    expect(listText).not.toContain('Alice');
    expect(listText).toContain('Bob');
  });

  test('should not add empty player name', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('#player-name', '   ');
    await page.click('#add-player-btn');
    
    // Player list should show "No players" message
    const listText = await page.locator('#player-list').textContent();
    expect(listText).toContain('No players');
  });

  test('should show player count', async ({ page }) => {
    await page.goto('/');
    
    // Add 3 players
    for (let i = 1; i <= 3; i++) {
      await page.fill('#player-name', `Player ${i}`);
      await page.click('#add-player-btn');
      // Wait a bit between additions
      await page.waitForTimeout(200);
    }
    
    // Wait for list to update
    await page.waitForTimeout(500);
    
    // Count list items
    const playerItems = page.locator('#player-list ol li');
    await expect(playerItems).toHaveCount(3);
  });
});
