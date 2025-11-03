#!/usr/bin/env node

/**
 * Comprehensive Test Runner
 * Runs all tests: E2E UI tests, Unit tests, and Integration tests
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import fs from 'fs';

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function logSection(title) {
  console.log('\n' + '='.repeat(60));
  log(title, colors.bright + colors.cyan);
  console.log('='.repeat(60) + '\n');
}

function runCommand(command, args, description) {
  return new Promise((resolve, reject) => {
    log(`▶️  ${description}`, colors.blue);
    log(`   Command: ${command} ${args.join(' ')}`, colors.reset);
    console.log();

    const startTime = Date.now();
    
    const child = spawn(command, args, {
      stdio: 'inherit',
      shell: true,
      cwd: process.cwd(),
    });

    child.on('error', (error) => {
      log(`❌ Error running ${description}: ${error.message}`, colors.red);
      reject(error);
    });

    child.on('close', (code) => {
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      
      if (code === 0) {
        log(`✅ ${description} - PASSED (${duration}s)`, colors.green);
        resolve({ success: true, duration, description });
      } else {
        log(`❌ ${description} - FAILED (exit code: ${code}, ${duration}s)`, colors.red);
        resolve({ success: false, duration, description, exitCode: code });
      }
    });
  });
}

async function runAllTests() {
  log('🧪 PICKLEBALL SESSION MANAGER - COMPREHENSIVE TEST SUITE', colors.bright + colors.magenta);
  log('Started at: ' + new Date().toLocaleString(), colors.yellow);
  console.log();

  const results = [];
  const startTime = Date.now();

  try {
    // 1. Configuration Check
    logSection('📋 Step 1: Configuration Check');
    const configCheck = await runCommand(
      'node',
      ['check-config.js'],
      'Configuration Validation'
    );
    results.push(configCheck);

    if (!configCheck.success) {
      log('\n⚠️  Configuration check failed. Stopping tests.', colors.yellow);
      log('Fix configuration issues before running tests.', colors.yellow);
      process.exit(1);
    }

    // 2. E2E Tests (Playwright)
    logSection('🌐 Step 2: End-to-End UI Tests (Playwright)');
    log('Testing in real browsers: Chromium, Firefox, WebKit, Mobile', colors.cyan);
    console.log();
    
    const e2eResult = await runCommand(
      'npx',
      ['-y', 'playwright@latest', 'test', '--reporter=list'],
      'E2E UI Tests (All Browsers)'
    );
    results.push(e2eResult);

    // 3. Unit Tests (if they exist)
    logSection('🔬 Step 3: Unit Tests (Vitest)');
    
    // Check if vitest tests exist
    const hasUnitTests = fs.existsSync('tests/unit') || 
                         fs.existsSync('src/__tests__') ||
                         fs.existsSync('vitest.config.ts');
    
    if (hasUnitTests) {
      const unitResult = await runCommand(
        'npm',
        ['run', 'test:run'],
        'Unit Tests (Round Robin, King of Court Logic)'
      );
      results.push(unitResult);
    } else {
      log('ℹ️  No unit tests found - skipping', colors.yellow);
      results.push({ 
        success: true, 
        duration: 0, 
        description: 'Unit Tests (skipped - not found)',
        skipped: true 
      });
    }

    // Summary
    logSection('📊 TEST RESULTS SUMMARY');
    
    const totalDuration = ((Date.now() - startTime) / 1000).toFixed(2);
    
    console.log();
    results.forEach((result, index) => {
      const icon = result.skipped ? 'ℹ️ ' : result.success ? '✅' : '❌';
      const status = result.skipped ? 'SKIPPED' : result.success ? 'PASSED' : 'FAILED';
      const statusColor = result.skipped ? colors.yellow : result.success ? colors.green : colors.red;
      
      log(`${icon} ${index + 1}. ${result.description}`, statusColor);
      log(`   Status: ${status} (${result.duration}s)`, colors.reset);
      
      if (result.exitCode && result.exitCode !== 0) {
        log(`   Exit Code: ${result.exitCode}`, colors.red);
      }
      console.log();
    });

    const passed = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success && !r.skipped).length;
    const skipped = results.filter(r => r.skipped).length;
    const total = results.length;

    console.log('─'.repeat(60));
    log(`Total: ${total} test suites`, colors.bright);
    log(`Passed: ${passed}`, colors.green);
    if (failed > 0) {
      log(`Failed: ${failed}`, colors.red);
    }
    if (skipped > 0) {
      log(`Skipped: ${skipped}`, colors.yellow);
    }
    log(`Duration: ${totalDuration}s`, colors.cyan);
    console.log('─'.repeat(60));
    console.log();

    if (failed === 0) {
      log('🎉 ALL TESTS PASSED! 🎉', colors.bright + colors.green);
      log('Your Pickleball Session Manager is ready to deploy! 🎾', colors.green);
      process.exit(0);
    } else {
      log('⚠️  SOME TESTS FAILED', colors.bright + colors.red);
      log('Review the failures above and fix the issues.', colors.yellow);
      log('Run individual test suites for more details:', colors.yellow);
      log('  - E2E: npx playwright test --ui', colors.cyan);
      log('  - Unit: npm run test:ui', colors.cyan);
      process.exit(1);
    }

  } catch (error) {
    log('\n❌ Test runner encountered an error:', colors.red);
    console.error(error);
    process.exit(1);
  }
}

// Show help
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log(`
${colors.bright}Pickleball Test Runner${colors.reset}

${colors.cyan}Usage:${colors.reset}
  node run-all-tests.js [options]

${colors.cyan}Options:${colors.reset}
  --help, -h     Show this help message

${colors.cyan}What it tests:${colors.reset}
  1. Configuration validation
  2. E2E UI tests (Playwright)
     - All browsers (Chromium, Firefox, WebKit)
     - Mobile browsers (Chrome, Safari)
     - All features and user workflows
  3. Unit tests (Vitest) - if they exist
     - Round Robin algorithm
     - King of the Court logic
     - Player management
     - Match scheduling

${colors.cyan}Quick commands:${colors.reset}
  Run all tests:           node run-all-tests.js
  Run E2E only:            npx playwright test
  Run E2E with UI:         npx playwright test --ui
  Run unit tests only:     npm run test
  Run unit tests with UI:  npm run test:ui

${colors.cyan}Test reports:${colors.reset}
  E2E report:    npx playwright show-report
  Unit report:   Check terminal output

${colors.cyan}Environment:${colors.reset}
  - Automatically starts dev server
  - Clears test state between runs
  - Tests against http://localhost:5173/pickleball/
  `);
  process.exit(0);
}

// Run tests
log('🚀 Starting comprehensive test suite...', colors.bright + colors.blue);
console.log();

runAllTests();
