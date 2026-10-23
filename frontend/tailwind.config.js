/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          dark: '#030712',
          panel: '#0B0F19',
          surface: '#1F2937',
          cyan: '#00F0FF',
          blue: '#3b82f6',
          violet: '#8b5cf6',
          border: '#1E293B',
          textMuted: '#94A3B8'
        }
      }
    },
  },
  plugins: [],
}
