import { defineConfig } from "vite";
export default defineConfig({
  base: "/doctor/",
  server: {
    host: "0.0.0.0",
    port: Number(process.env.PORT || 5173),
    allowedHosts: true,
    proxy: {
      "/clinical": {
        target: process.env.CLINICAL_API_URL || "http://127.0.0.1:8060",
        changeOrigin: false,
      },
    },
  },
});
