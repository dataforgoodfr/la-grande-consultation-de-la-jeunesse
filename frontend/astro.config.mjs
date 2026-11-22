// @ts-check
import { defineConfig, fontProviders } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
	vite: {
		plugins: [tailwindcss()],
	},
	fonts: [
		{
			// Placeholder for Cardust (main headings) until licensing is confirmed
			provider: fontProviders.local(),
			name: 'Knewave',
			cssVariable: '--font-knewave',
			fallbacks: ['cursive'],
			options: {
				variants: [
					{
						src: ['./src/assets/fonts/knewave/Knewave-Regular.ttf'],
						weight: 400,
						style: 'normal',
					},
				],
			},
		},
		{
			// Body text
			provider: fontProviders.local(),
			name: 'Afacad',
			cssVariable: '--font-afacad',
			fallbacks: ['sans-serif'],
			options: {
				variants: [
					{
						src: ['./src/assets/fonts/afacad/Afacad-Variable.ttf'],
						weight: '400 700',
						style: 'normal',
					},
				],
			},
		},
	],
});
