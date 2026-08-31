/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const backendTarget = process.env.VITE_API_BASE_URL || "http://localhost:8000";
const backendProxy = {
  "/api": {
    target: backendTarget,
    changeOrigin: true,
  },
  "/health": {
    target: backendTarget,
    changeOrigin: true,
  },
  "/ready": {
    target: backendTarget,
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: backendProxy,
  },
  preview: {
    port: 4173,
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "open-bim-mvp.mirai-dx-platform.com",
      "open-bim.mirai-dx-platform.com",
    ],
    proxy: backendProxy,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Only run vitest unit tests under src/; Playwright owns e2e/
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
