import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const flaskApiOrigin = env.VITE_FLASK_API_ORIGIN?.trim() || 'http://127.0.0.1:5000';

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['logo.svg', 'icon.svg', 'apple-touch-icon.png'],
        manifest: {
          id: '/',
          name: 'NexHaat Marketplace',
          short_name: 'NexHaat',
          description: "NexHaat is Bangladesh's premier hyper-local multivendor marketplace for fresh foods, groceries, electronics, and local products.",
          theme_color: '#1769FF',
          background_color: '#F3F4F6',
          display: 'standalone',
          start_url: '/',
          scope: '/',
          icons: [
            {
              src: '/pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/pwa-maskable-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'gstatic-fonts-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
          ],
        },
        // Keep generated service-worker output out of `vite dev` unless the
        // developer opts in, so development does not rewrite `dev-dist/`.
        devOptions: {
          enabled: env.VITE_PWA_DEV === 'true',
          type: 'module',
        },
      }),
    ],
    build: {
      rollupOptions: {
        output: {
          // Split large, route-independent vendors out of the entry chunk so the
          // first paint does not download Firebase and charting code.
          manualChunks: {
            'vendor-react': ['react', 'react-dom'],
            'vendor-firebase': ['firebase/app', 'firebase/auth', 'firebase/firestore'],
            'vendor-charts': ['recharts'],
          },
        },
      },
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      allowedHosts: true,
      hmr: false,
      proxy: {
        // Forward same-origin React requests to Flask during local development.
        '/api': {
          target: flaskApiOrigin,
          changeOrigin: true,
        },
        '/auth': {
          target: flaskApiOrigin,
          changeOrigin: true,
        },
      },
    },
  };
});

