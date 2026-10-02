import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forwards /api/* to the FastAPI backend during dev, so frontend code
    // only ever calls relative paths — identical in dev and in the
    // deployed single-container setup where FastAPI serves both.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
})
