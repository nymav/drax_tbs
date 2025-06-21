/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        palletBg: '#0B0D17',          // dark background
        palletText: '#E0E6F3',        // off-white text
        palletAccent: '#5A82F5',      // neon-ish blue accent
        neonBlue: '#53f',
        neonPurple: '#a2f',
        panelBg: 'rgba(20,24,42,0.8)',
        palletBorder: '#2E334D',
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        sans: ['ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      animation: {
        flicker: 'flicker 3s infinite',
        pulseFast: 'pulse 1s infinite',
        fadeIn: 'fadeIn 0.5s ease-out both',
      },
      keyframes: {
        flicker: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.8 },
        },
        fadeIn: {
          from: {
            opacity: 0,
            transform: 'translateY(10px)',
          },
          to: {
            opacity: 1,
            transform: 'translateY(0)',
          },
        },
      },
      textShadow: {
        neonBlue: '0 0 6px #5A82F5, 0 0 12px #5A82F5',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      addUtilities({
        '.text-shadow-neonBlue': {
          'text-shadow': '0 0 6px #5A82F5, 0 0 12px #5A82F5',
        },
      });
    },
  ],
};