/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    darkMode: 'class',
    theme: {
        screens: {
            xs: "480px",
            sm: "640px",
            md: "768px",
            lg: "1024px",
            xl: "1140px",
            "2xl": "1280px",
        },
        container: {
            center: true,
        },
        extend: {
            keyframes: {
              animateGradient: {
                '0%' : { 'background-position': '0% 50%'},
                '50%' : { 'background-position': '100% 50%'},
                '100%' : { 'background-position': '0% 50%'},
              },
            },
          },
    },
    plugins: [
        require("@tailwindcss/forms"),
        require('@tailwindcss/typography'),
        require("@headlessui/tailwindcss"),
        require("tailwind-scrollbar"),
        // ...
    ],
};
