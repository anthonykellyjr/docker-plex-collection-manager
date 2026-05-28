import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { idleShutdown } from './vite/idle-shutdown.js'

export default defineConfig({
  plugins: [vue(), idleShutdown()],
  base: '/collections/',
  server: {
    open: '/collections/',
    proxy: {
      '/capi': {
        // Dev only: Vite runs inside a node:22-alpine container, so localhost is the
        // container, not the host. Reach the host-published collection-api (5060->5000)
        // via host.docker.internal (the dev container is started with --add-host).
        target: 'http://host.docker.internal:5060',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyDirOnBuild: true,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          'vue': ['vue']
        }
      }
    }
  }
})
