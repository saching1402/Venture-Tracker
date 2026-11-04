import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // dev: forward API calls to the local Django server
    proxy: { '/api': 'http://localhost:8000', '/admin': 'http://localhost:8000', '/static': 'http://localhost:8000' },
  },
})
