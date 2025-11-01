import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      // Proxy ONLY API endpoints; do NOT proxy the React route /auth/callback
      '/auth': { 
        target: 'http://localhost:5000', 
        changeOrigin: true,
        cookieDomainRewrite: 'localhost',
        cookiePathRewrite: '/',
      },
      '/detect': { target: 'http://localhost:5000', changeOrigin: true },
      '/live': { target: 'http://localhost:5000', changeOrigin: true },
      '/results': { target: 'http://localhost:5000', changeOrigin: true },
      '/history': { target: 'http://localhost:5000', changeOrigin: true },
      '/download': { target: 'http://localhost:5000', changeOrigin: true },
    }
  }
})
