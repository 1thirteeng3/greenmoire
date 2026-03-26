/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Forçamos o dark mode como padrão
  theme: {
    extend: {
      colors: {
        // Fundo e Superfícies (Estética Obsidian/Cofre)
        vault: {
          900: '#0F1115', // Fundo principal
          800: '#181A1F', // Paineis laterais
          700: '#21252B', // Hover states e bordas
        },
        // Sinais Cognitivos (Para o Modo Advanced)
        cognitive: {
          t1: '#61AFEF', // Azul (Rápido, Gatekeeper)
          t2: '#C678DD', // Púrpura (Analítico, Auditor)
          t3: '#E5C07B', // Âmbar (Complexo, Executor)
          success: '#98C379', // Verde (Aprovado)
          alert: '#E06C75',   // Vermelho (Falha/Alucinação)
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['Fira Code', 'JetBrains Mono', 'monospace'], // Crucial para logs e JSON
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'), // Essencial para renderizar Markdown impecável
  ],
}
