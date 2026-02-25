import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				},
				// Semantic theme tokens driven by CSS variables so the
				// existing dark/light mode switch can swap palettes.
				background: 'var(--color-background)',
				foreground: 'var(--color-foreground)',
				surface: 'var(--color-surface)',
				'surface-elevated': 'var(--color-surface-elevated)',
				border: 'var(--color-border)',
				primary: {
					50: 'var(--color-primary-50, #fff1f2)',
					100: 'var(--color-primary-100, #ffe4e6)',
					200: 'var(--color-primary-200, #fecdd3)',
					300: 'var(--color-primary-300, #fda4af)',
					400: 'var(--color-primary-400, #fb7185)',
					500: 'var(--color-primary-500, #ef4444)',
					600: 'var(--color-primary-600, #dc2626)',
					700: 'var(--color-primary-700, #b91c1c)',
					800: 'var(--color-primary-800, #991b1b)',
					900: 'var(--color-primary-900, #7f1d1d)'
				},
				primaryForeground: 'var(--color-primary-foreground)'
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			borderRadius: {
				'btn': '9999px',
				'xl': '0.9rem'
			}
		}
	},
	plugins: [typography, containerQuries]
};
