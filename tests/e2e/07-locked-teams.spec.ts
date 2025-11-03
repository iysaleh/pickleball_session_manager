import { test, expect } from '@playwright/test';

test.describe('Locked Teams', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should show locked teams option for doubles', async ({ page }) => {
    await page.goto('/');
    
    // Select doubles
    await page.selectOption('#session-type', 'doubles');
    
    // Locked teams container should be visible
    await expect(page.locator('#locked-teams-container')).toBeVisible();
  });

  test('should hide locked teams option for singles', async ({ page }) => {
    await page.goto('/');
    
    // Select singles
    await page.selectOption('#session-type', 'singles');
    
    // Locked teams container should be hidden
    await expect(page.locator('#locked-teams-container')).toBeHidden();
  });

  test('should enable locked teams mode', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Locked teams setup should be visible
    await expect(page.locator('#locked-teams-setup')).toBeVisible();
  });

  test('should add a locked team', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Add a team
    await page.fill('#team-player1-name', 'Alice');
    await page.fill('#team-player2-name', 'Bob');
    await page.click('#add-locked-team-btn');
    
    // Team should appear in list
    const teamsList = page.locator('#locked-teams-list');
    await expect(teamsList).toContainText('Alice');
    await expect(teamsList).toContainText('Bob');
  });

  test('should add multiple locked teams', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Add first team
    await page.fill('#team-player1-name', 'Alice');
    await page.fill('#team-player2-name', 'Bob');
    await page.click('#add-locked-team-btn');
    
    // Add second team
    await page.fill('#team-player1-name', 'Charlie');
    await page.fill('#team-player2-name', 'Diana');
    await page.click('#add-locked-team-btn');
    
    // Both teams should be visible
    const teamsList = page.locator('#locked-teams-list');
    await expect(teamsList).toContainText('Alice & Bob');
    await expect(teamsList).toContainText('Charlie & Diana');
  });

  test('should require 2+ teams to start session', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    const startBtn = page.locator('#start-session-btn');
    await expect(startBtn).toBeDisabled();
    
    // Add one team
    await page.fill('#team-player1-name', 'Alice');
    await page.fill('#team-player2-name', 'Bob');
    await page.click('#add-locked-team-btn');
    await expect(startBtn).toBeDisabled();
    
    // Add second team
    await page.fill('#team-player1-name', 'Charlie');
    await page.fill('#team-player2-name', 'Diana');
    await page.click('#add-locked-team-btn');
    await expect(startBtn).toBeEnabled();
  });

  test('should start session with locked teams', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Add 3 teams
    const teams = [
      ['Alice', 'Bob'],
      ['Charlie', 'Diana'],
      ['Eve', 'Frank']
    ];
    
    for (const [p1, p2] of teams) {
      await page.fill('#team-player1-name', p1);
      await page.fill('#team-player2-name', p2);
      await page.click('#add-locked-team-btn');
    }
    
    await page.click('#start-session-btn');
    
    // Session should start
    await expect(page.locator('#control-section')).toBeVisible();
  });

  test('should remove a locked team', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Add teams
    await page.fill('#team-player1-name', 'Alice');
    await page.fill('#team-player2-name', 'Bob');
    await page.click('#add-locked-team-btn');
    
    await page.fill('#team-player1-name', 'Charlie');
    await page.fill('#team-player2-name', 'Diana');
    await page.click('#add-locked-team-btn');
    
    // Remove first team
    const removeBtn = page.locator('#locked-teams-list button').first();
    await removeBtn.click();
    
    // First team should be gone
    const teamsList = page.locator('#locked-teams-list');
    const text = await teamsList.textContent();
    expect(text).not.toContain('Alice & Bob');
    expect(text).toContain('Charlie & Diana');
  });

  test('should add team with Enter key navigation', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    // Fill first name and press Enter
    await page.fill('#team-player1-name', 'Alice');
    await page.press('#team-player1-name', 'Enter');
    
    // Focus should move to second field
    await page.fill('#team-player2-name', 'Bob');
    await page.press('#team-player2-name', 'Enter');
    
    // Team should be added
    await expect(page.locator('#locked-teams-list')).toContainText('Alice & Bob');
  });

  test('should clear team inputs after adding', async ({ page }) => {
    await page.goto('/');
    
    await page.selectOption('#session-type', 'doubles');
    await page.check('#locked-teams-checkbox');
    
    await page.fill('#team-player1-name', 'Alice');
    await page.fill('#team-player2-name', 'Bob');
    await page.click('#add-locked-team-btn');
    
    // Inputs should be cleared
    await expect(page.locator('#team-player1-name')).toHaveValue('');
    await expect(page.locator('#team-player2-name')).toHaveValue('');
  });
});
