import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/sfitest/', // Setting base path for the specific URL requirements
  build: {
    outDir: '../public/sfitest', // Build directly into the hosting public folder
    emptyOutDir: true
  }
})
