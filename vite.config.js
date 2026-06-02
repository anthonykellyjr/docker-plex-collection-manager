import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Served at the domain root by default. Set VITE_BASE (e.g. /collections/) to host
// it under a sub-path. VITE_API_TARGET points the dev proxy at the running backend.
export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE || '/',
  server: {
    proxy: {
      '/capi': {
        target: process.env.VITE_API_TARGET || 'http://localhost:5060',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    minify: 'esbuild',
    rollupOptions: {
      output: { manualChunks: { vue: ['vue'] } },
    },
  },
})
