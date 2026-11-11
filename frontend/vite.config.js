import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The page calls /api/... on its own address and Vite passes those calls on to the
// backend. That way the browser never makes a cross-site request (no CORS issues,
// and it works inside VS Code's built-in browser too).
const backend = "http://127.0.0.1:8000";
const proxy = { "/api": { target: backend, changeOrigin: true } };

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    allowedHosts: [".trycloudflare.com"],
    proxy,
  },
  preview: { port: 5173, strictPort: true, proxy },
});
