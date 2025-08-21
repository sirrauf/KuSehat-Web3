export default defineNuxtConfig({
  ssr: false, // Penting untuk aplikasi IC agar berjalan di client-side
  vite: {
    optimizeDeps: {
      include: ["@dfinity/agent", "@dfinity/candid"],
    },
  },
});