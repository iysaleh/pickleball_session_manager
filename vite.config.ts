import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  base: '/pickleball/', // Replace with your repo name
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
});
