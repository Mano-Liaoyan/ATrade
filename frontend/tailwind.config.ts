import type { Config } from "tailwindcss";

const config = {
  darkMode: ["class", "[data-theme='dark']"],
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx,mdx}",
    "./lib/**/*.{ts,tsx,mdx}",
    "./types/**/*.{ts,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        terminal: {
          canvas: "hsl(var(--terminal-canvas))",
          surface: "hsl(var(--terminal-surface))",
          elevated: "hsl(var(--terminal-surface-elevated))",
          inset: "hsl(var(--terminal-surface-inset))",
          border: "hsl(var(--terminal-border))",
          grid: "hsl(var(--terminal-grid))",
          splitter: "hsl(var(--terminal-splitter))",
          text: "hsl(var(--terminal-text))",
          muted: "hsl(var(--terminal-text-muted))",
          subtle: "hsl(var(--terminal-text-subtle))",
          amber: "hsl(var(--terminal-accent-amber))",
          cyan: "hsl(var(--terminal-accent-cyan))",
          green: "hsl(var(--terminal-accent-green))",
          red: "hsl(var(--terminal-accent-red))",
          blue: "hsl(var(--terminal-accent-blue))",
        },
        status: {
          neutral: "hsl(var(--status-neutral))",
          info: "hsl(var(--status-info))",
          success: "hsl(var(--status-success))",
          warning: "hsl(var(--status-warning))",
          danger: "hsl(var(--status-danger))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        "terminal-panel": "var(--shadow-terminal-panel)",
        "terminal-glow": "var(--shadow-terminal-glow)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      screens: {
        terminal: "1180px",
        widescreen: "1440px",
      },
    },
  },
} satisfies Config;

export default config;
