#!/usr/bin/env node

/**
 * Configuration Validation Script
 * Run this before starting the dev server to catch config issues early
 */

console.log('🔍 Checking configuration files...\n');

const fs = require('fs');
const path = require('path');

let hasErrors = false;

// Check 1: vite.config.ts exists and is valid
console.log('📝 Checking vite.config.ts...');
try {
  const viteConfig = fs.readFileSync('vite.config.ts', 'utf8');
  
  // Check for problematic imports that require installed packages
  if (viteConfig.includes('import') && viteConfig.includes('from')) {
    const importMatch = viteConfig.match(/import.*from\s+['"](.+)['"]/);
    if (importMatch) {
      const importPackage = importMatch[1];
      // Check if trying to import from a package that might not be installed
      if (!importPackage.startsWith('.') && !importPackage.startsWith('/')) {
        console.warn(`   ⚠️  Warning: vite.config.ts imports from '${importPackage}'`);
        console.warn('   This requires the package to be installed.');
        console.warn('   Consider using plain export default {} for local dev.\n');
      }
    }
  } else {
    console.log('   ✅ vite.config.ts uses plain export (good for local dev)\n');
  }
} catch (err) {
  console.error(`   ❌ Error reading vite.config.ts: ${err.message}\n`);
  hasErrors = true;
}

// Check 2: playwright.config.ts
console.log('📝 Checking playwright.config.ts...');
try {
  const playwrightConfig = fs.readFileSync('playwright.config.ts', 'utf8');
  
  if (playwrightConfig.includes('import')) {
    console.log('   ℹ️  playwright.config.ts has imports (requires @playwright/test installed)\n');
  } else {
    console.log('   ✅ playwright.config.ts checked\n');
  }
} catch (err) {
  console.log(`   ℹ️  playwright.config.ts not found or not readable (okay if not running tests)\n`);
}

// Check 3: package.json
console.log('📝 Checking package.json...');
try {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  
  // Check scripts
  if (packageJson.scripts) {
    console.log('   ✅ Scripts found:');
    Object.keys(packageJson.scripts).forEach(script => {
      console.log(`      - ${script}`);
    });
    console.log();
  }
  
  // Check for devDependencies
  if (packageJson.devDependencies) {
    const depCount = Object.keys(packageJson.devDependencies).length;
    console.log(`   📦 ${depCount} devDependencies listed\n`);
  }
} catch (err) {
  console.error(`   ❌ Error reading package.json: ${err.message}\n`);
  hasErrors = true;
}

// Check 4: index.html
console.log('📝 Checking index.html...');
try {
  const html = fs.readFileSync('index.html', 'utf8');
  
  if (html.includes('type="module"')) {
    console.log('   ✅ index.html uses ES modules\n');
  }
  
  if (html.includes('src/main.ts')) {
    console.log('   ✅ index.html references src/main.ts\n');
  }
} catch (err) {
  console.error(`   ❌ Error reading index.html: ${err.message}\n`);
  hasErrors = true;
}

// Check 5: src/main.ts
console.log('📝 Checking src/main.ts...');
try {
  const mainTs = fs.readFileSync('src/main.ts', 'utf8');
  console.log(`   ✅ src/main.ts exists (${mainTs.length} bytes)\n`);
} catch (err) {
  console.error(`   ❌ Error reading src/main.ts: ${err.message}\n`);
  hasErrors = true;
}

// Check 6: node_modules
console.log('📝 Checking node_modules...');
try {
  if (fs.existsSync('node_modules')) {
    const nodeModulesContents = fs.readdirSync('node_modules');
    console.log(`   📦 node_modules exists with ${nodeModulesContents.length} items\n`);
    
    if (nodeModulesContents.length < 10) {
      console.warn('   ⚠️  Warning: node_modules seems incomplete');
      console.warn('   Expected hundreds of packages, found only ' + nodeModulesContents.length);
      console.warn('   You may need to run: rm -rf node_modules package-lock.json && npm install\n');
    }
  } else {
    console.warn('   ⚠️  node_modules does not exist');
    console.warn('   Run: npm install\n');
  }
} catch (err) {
  console.error(`   ❌ Error checking node_modules: ${err.message}\n`);
}

// Summary
console.log('━'.repeat(60));
if (hasErrors) {
  console.log('❌ Configuration check found errors!');
  console.log('   Fix the errors above before starting the dev server.\n');
  process.exit(1);
} else {
  console.log('✅ Configuration check passed!');
  console.log('   You can start the dev server with: npx -y vite@latest\n');
  process.exit(0);
}
