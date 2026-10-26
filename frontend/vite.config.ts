import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5188,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8018', timeout: 360000 } },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], css: false },
  build: {
    rolldownOptions: {
      output: {
        manualChunks(id) {
          if (/recharts|victory|d3-/.test(id)) return 'charts'
          if (id.includes('@copilotkit') || id.includes('@a2ui')) return 'a2ui'
        },
      },
    },
  },
})
