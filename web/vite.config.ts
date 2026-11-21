/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// `base` is relative so the build also works under GitHub Pages (/simulator/).
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@design": fileURLToPath(new URL("../design", import.meta.url)),
      "@locales": fileURLToPath(new URL("./locales", import.meta.url)),
    },
  },
  server: { fs: { allow: [".."] } },
  // Pyodide ships its own loader; let it load its files at run time instead of pre-bundling.
  optimizeDeps: { exclude: ["pyodide"] },
  worker: { format: "es" },
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("./index.html", import.meta.url)),
        "engine-test": fileURLToPath(new URL("./engine-test.html", import.meta.url)),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    exclude: ["**/node_modules/**", "**/dist/**", ...(process.env.PYODIDE_DIST ? [] : ["**/*.spike.test.ts"])],
  },
});
