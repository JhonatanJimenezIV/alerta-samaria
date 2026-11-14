import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// El frontend llama a /api/... y Vite lo reenvía al API Gateway del emulador.
// Así el navegador no hace peticiones cross-origin (sin problemas de CORS) y
// cuando cambia el api-id solo se actualiza .env.local (lo hace deploy.sh).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const destino = env.VITE_API_URL || "";
  const url = destino ? new URL(destino) : null;
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: url
        ? {
            "/api": {
              target: url.origin,
              changeOrigin: true,
              rewrite: (ruta) => ruta.replace(/^\/api/, url.pathname.replace(/\/$/, "")),
            },
          }
        : undefined,
    },
  };
});
