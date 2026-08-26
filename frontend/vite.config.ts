import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // Default: normal dev backend on :8000 -> ali_trading. Overridden
        // only for the isolated Playwright E2E frontend instance (started on
        // a separate port, see frontend/e2e/auth.spec.ts), which sets this
        // to point at the isolated :8001 backend -> ali_trading_test.
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
