import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    // Exclude Playwright E2E tests - they use .spec.ts
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/e2e/**',
      '**/*.spec.ts',
    ],
    // Include only unit tests - they use .test.ts
    include: [
      'src/**/*.test.ts',
      'tests/unit/**/*.test.ts',
    ],
  },
});
