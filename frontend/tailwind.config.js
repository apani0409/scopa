/** @type {import('tailwindcss').Config} */
export default {
    content: ['./src/**/*.{html,js,svelte}'],
    theme: {
        extend: {
            colors: {
                felt: {
                    dark:    '#1a4731',
                    DEFAULT: '#2d6a4f',
                    light:   '#40916c',
                },
            },
            keyframes: {
                'card-deal': {
                    '0%':   { transform: 'scale(0.85) translateY(16px)', opacity: '0' },
                    '100%': { transform: 'scale(1)    translateY(0)',     opacity: '1' },
                },
                'slide-down': {
                    '0%':   { transform: 'translateY(-12px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)',      opacity: '1' },
                },
            },
            animation: {
                'card-deal': 'card-deal 0.28s ease-out both',
                'slide-down': 'slide-down 0.2s ease-out both',
            },
        },
    },
    plugins: [],
};
