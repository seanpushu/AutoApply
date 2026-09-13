import { sites } from '@openai/sites-vite-plugin';
import tailwindcss from '@tailwindcss/postcss';
import vinext from 'vinext';
import { defineConfig } from 'vite';

// This client-only workspace is exported as static assets. The optional local
// Python service owns disk persistence; hosted operation uses browser storage.
export default defineConfig({
  css: { postcss: { plugins: [tailwindcss()] } },
  build: { emptyOutDir: false },
  plugins: [vinext(), sites()],
});
