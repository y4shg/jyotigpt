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
				red: {
					50: 'var(--color-red-50, #FEF0F0)',
					100: 'var(--color-red-100, #fee2e2)',
					200: 'var(--color-red-200, #fecaca)',
					300: 'var(--color-red-300, #fca5a5)',
					400: 'var(--color-red-400, #f87171)',
					500: 'var(--color-red-500, #ef4444)',
					600: 'var(--color-red-600, #E82020)',
					700: 'var(--color-red-700, #EF3535)',
					800: 'var(--color-red-800, #991b1b)',
					900: 'var(--color-red-900, #3A1818)',
					950: 'var(--color-red-950, #450a0a)'
				}
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
			}
		}
	},
	plugins: [typography, containerQuries]
};
