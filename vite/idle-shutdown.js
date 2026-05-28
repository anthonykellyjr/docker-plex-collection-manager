/**
 * idle-shutdown — Vite plugin that auto-terminates the dev server after a
 * configurable period of no HTTP/WS activity.
 *
 * Why: developers (me) leave `dev.sh` running in a forgotten tmux pane, the
 * node process consumes ~200MB RSS per app, and HMR websockets stay open
 * indefinitely. After 30 min of nobody actually opening the browser, the
 * dev server is dead weight. This plugin kills it cleanly.
 *
 * Usage in a vite.config.js (per app):
 *   import { idleShutdown } from '../packages/shared/vite/idle-shutdown.js'
 *   export default defineConfig({
 *     plugins: [vue(), idleShutdown()],   // 30 min default
 *     // or: idleShutdown({ idleMs: 15 * 60 * 1000 })
 *   })
 *
 * Activity is anything that hits a Vite middleware:
 *   - GET /index.html, /src/*, /@vite/* (browser requests + HMR refreshes)
 *   - WebSocket HMR connection events
 *
 * Cost: one setInterval(checkMs) that does `Date.now() - lastActivity`.
 * Sub-microsecond per tick at the default 60s cadence. The interval is
 * `unref()`'d so it never holds the event loop open on its own.
 *
 * Build-only behavior: this plugin's hooks are only configureServer-based,
 * so `vite build` paths through with zero effect.
 */
export function idleShutdown(opts = {}) {
  const idleMs  = opts.idleMs  ?? 30 * 60 * 1000   // 30 minutes
  const checkMs = opts.checkMs ?? 60 * 1000        // poll once a minute

  return {
    name: 'idle-shutdown',
    apply: 'serve',                                // never runs during `vite build`
    configureServer(server) {
      let lastActivity = Date.now()

      // HTTP requests bump activity.
      server.middlewares.use((_req, _res, next) => {
        lastActivity = Date.now()
        next()
      })

      // HMR websocket connect / message events also count.
      const ws = server.ws
      if (ws) {
        ws.on?.('connection', () => { lastActivity = Date.now() })
      }

      const interval = setInterval(async () => {
        const idleFor = Date.now() - lastActivity
        if (idleFor >= idleMs) {
          const mins = Math.round(idleFor / 60000)
          // Use stderr so it's still visible if stdout is captured somewhere.
          process.stderr.write(`\n[idle-shutdown] No activity for ${mins} min — terminating Vite dev server.\n`)
          clearInterval(interval)
          try { await server.close() } catch { /* shutting down, ignore */ }
          process.exit(0)
        }
      }, checkMs)
      // Don't keep the event loop alive on this timer alone — server's HTTP
      // listener does that. Means `process.exit()` works promptly.
      interval.unref?.()

      const idleMins = Math.round(idleMs / 60000)
      process.stderr.write(`[idle-shutdown] armed: will auto-exit after ${idleMins} min of inactivity.\n`)
    },
  }
}
