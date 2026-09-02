/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        avionics: {
          bg: '#0B0F14',
          surface: '#111722',
          card: '#161F2E',
          cardHover: '#1C273A',
          border: '#1E293B',
          borderLight: '#334155',
          borderAccent: '#0284C7',
          cyan: '#00F0FF',
          cyanMuted: '#0891B2',
          nominal: '#10B981',
          nominalBg: 'rgba(16, 185, 129, 0.1)',
          warning: '#F59E0B',
          warningBg: 'rgba(245, 158, 11, 0.12)',
          critical: '#EF4444',
          criticalBg: 'rgba(239, 68, 68, 0.15)',
          muted: '#64748B',
          text: '#F1F5F9',
          textSecondary: '#94A3B8',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'glow-cyan': '0 0 15px -3px rgba(0, 240, 255, 0.3)',
        'glow-nominal': '0 0 15px -3px rgba(16, 185, 129, 0.35)',
        'glow-warning': '0 0 15px -3px rgba(245, 158, 11, 0.35)',
        'glow-critical': '0 0 20px -2px rgba(239, 68, 68, 0.45)',
        'hud': 'inset 0 0 20px rgba(0, 240, 255, 0.05)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'strobe-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
