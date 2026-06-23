import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// VITE_API_URL controls the backend base URL (defaults to localhost:8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
