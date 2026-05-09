import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
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
