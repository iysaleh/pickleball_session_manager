// https://vitejs.dev/config/
export default {
  base: '/', // Root domain for BetterPickleballSessions.com
  publicDir: 'public', // Ensure CNAME is copied to dist
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
};
