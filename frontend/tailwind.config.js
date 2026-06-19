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
        deepNavy: '#0D1B2A',
        electricBlue: '#1E6FE8',
        cyberTeal: '#00C8B4',
        softSlate: '#4A5568',
        cloudWhite: '#F7F9FC',
        signalAmber: '#F59E0B',
        alertRed: '#EF4444',
        successGreen: '#10B981',
        indigoBrand: '#6366F1',
        
        // Dark Mode Overrides mapping
        darkAppBg: '#0D1B2A',
        darkSidebarBg: '#0A1628',
        darkCardBg: '#1A2940',
        darkModalBg: '#243347',
        darkPrimaryText: '#F7F9FC',
        darkSecondaryText: '#94A3B8',
        darkBorder: '#2D3F56',

        // Light Mode Overrides mapping
        lightAppBg: '#F7F9FC',
        lightSidebarBg: '#FFFFFF',
        lightCardBg: '#FFFFFF',
        lightModalBg: '#FFFFFF',
        lightPrimaryText: '#0D1B2A',
        lightSecondaryText: '#4A5568',
        lightBorder: '#E2E8F0',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        'xs': '4px',
        'sm': '8px',
        'md-sm': '12px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
        '2xl': '48px',
        '3xl': '64px',
      },
      borderRadius: {
        'sharp': '4px',
        'default': '8px',
        'large': '12px',
      },
      boxShadow: {
        'sm': '0 1px 2px rgba(0,0,0,0.06)',
        'md': '0 4px 12px rgba(0,0,0,0.10)',
        'lg': '0 8px 32px rgba(0,0,0,0.16)',
      },
      transitionDuration: {
        'standard': '150ms',
        'panel': '200ms',
        'toast': '300ms',
      }
    },
  },
  plugins: [],
}
