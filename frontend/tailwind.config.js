export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { ink: '#111827', trust: '#0f766e', signal: '#2563eb', amberline: '#f59e0b' },
      boxShadow: { soft: '0 10px 30px rgba(17, 24, 39, 0.08)' },
    },
  },
  plugins: [],
};
