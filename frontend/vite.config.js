import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",         // 👈 Expose frontend to local network
    port: 5173,              // 👈 Optional, you can change if needed
    strictPort: true,        // 🔒 Ensures Vite uses this exact port
  },
});