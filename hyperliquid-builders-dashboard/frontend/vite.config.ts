import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            // Suppress EPIPE errors during WebSocket reconnection
            if ((err as NodeJS.ErrnoException).code !== 'EPIPE') {
              console.error('WebSocket proxy error:', err.message);
            }
          });
        },
      },
    },
  },
});
