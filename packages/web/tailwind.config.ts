import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Figtree', 'system-ui', 'sans-serif'],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        border: "var(--border)",
        ring: "var(--ring)",
        sidebar: "var(--sidebar)",
      },
      borderRadius: {
        xl: "var(--radius)",
        lg: "16px",
        md: "12px",
        sm: "8px",
        pill: "9999px",
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
