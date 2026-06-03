import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Served at the domain root by default. Set VITE_BASE (e.g. /collections/) to host
// it under a sub-path. VITE_API_TARGET points the dev proxy at the running backend.
export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE || '/',
  // Where the app's API lives. Defaults to /capi (app at the domain root). Set
  // VITE_API_BASE to serve under a subpath, e.g. /demos/collection-manager/capi.
  define: {
    'import.meta.env.VITE_API_BASE': JSON.stringify(process.env.VITE_API_BASE || '/capi'),
  },
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
