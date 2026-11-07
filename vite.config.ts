import { defineConfig, loadEnv, PluginOption } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(async ({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const flaskApiOrigin = env.VITE_FLASK_API_ORIGIN?.trim();

  const plugins: PluginOption[] = [react()];
  if (command === 'build') {
    const { VitePWA } = await import('vite-plugin-pwa');
    plugins.push(
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
        devOptions: {
          enabled: env.VITE_PWA_DEV === 'true',
          type: 'module',
        },
      }),
    );
  }

  return {
    plugins,
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
      proxy: flaskApiOrigin
        ? {
            // Forward same-origin React requests to configured Flask origin during local development.
            '/api': {
              target: flaskApiOrigin,
              changeOrigin: true,
              configure: (proxy) => {
                proxy.on('error', (_err, _req, res) => {
                  if (res && !res.headersSent && typeof res.writeHead === 'function') {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(
                      JSON.stringify({
                        success: false,
                        error: { code: 'BACKEND_UNAVAILABLE', message: 'Flask backend is unavailable.' },
                      }),
                    );
                  }
                });
              },
            },
            '/auth': {
              target: flaskApiOrigin,
              changeOrigin: true,
            },
          }
        : undefined,
    },
  };
});

