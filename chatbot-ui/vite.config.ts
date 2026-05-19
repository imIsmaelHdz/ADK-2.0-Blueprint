import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const srcDir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(srcDir, './src'),
    },
  },
  plugins: [tailwindcss(), react()],
  server: {
    proxy: {
      // FastAPI gateway (recommended for local dev to avoid CORS)
      '/v1': {
        target: 'http://localhost:8011',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8011',
        changeOrigin: true,
      },
    },
  },
})
