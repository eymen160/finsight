import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        // ── FinSight Design Tokens ──────────────────────────────
        // Base dark slate palette — "smart old money" terminal
        canvas:   { DEFAULT: "#05080f", 900: "#080c14", 800: "#0c1120", 700: "#111827" },
        surface:  { DEFAULT: "#111827", muted: "#1a2235", border: "rgba(255,255,255,0.06)" },
        // Text hierarchy
        ink:      { high: "#f0f4f8", mid: "#94a3b8", low: "#475569", muted: "#1e293b" },
        // Accent — electric blue (Robinhood-meets-Bloomberg)
        accent:   {
          DEFAULT: "#3b82f6",
          dim:     "rgba(59,130,246,0.15)",
          glow:    "rgba(59,130,246,0.3)",
          50:  "#eff6ff",
          100: "#dbeafe",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
        },
        // Signal colors — green/red/yellow for market data
        bull:    { DEFAULT: "#22c55e", dim: "rgba(34,197,94,0.12)",  text: "#4ade80"  },
        bear:    { DEFAULT: "#ef4444", dim: "rgba(239,68,68,0.12)",  text: "#f87171"  },
        caution: { DEFAULT: "#eab308", dim: "rgba(234,179,8,0.12)",  text: "#fbbf24"  },
        // shadcn/ui compatible
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent_ui: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
        mono: ["var(--font-jetbrains)", "JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "1rem" }],
        xs:   ["0.75rem",  { lineHeight: "1rem"  }],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        // Glow effects for active states
        "accent-sm":  "0 0 12px rgba(59,130,246,0.25)",
        "accent-md":  "0 0 24px rgba(59,130,246,0.3)",
        "bull-sm":    "0 0 12px rgba(34,197,94,0.25)",
        "bear-sm":    "0 0 12px rgba(239,68,68,0.25)",
        "card":       "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.6)",
        "card-hover": "0 4px 20px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.2)",
      },
      keyframes: {
        "accordion-down":   { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up":     { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        "fade-in":          { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "slide-in-right":   { from: { transform: "translateX(100%)" }, to: { transform: "translateX(0)" } },
        "slide-in-left":    { from: { transform: "translateX(-100%)" }, to: { transform: "translateX(0)" } },
        "pulse-dot":        { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.3" } },
        "shimmer":          { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        "blink-cursor":     { "0%,100%": { borderColor: "transparent" }, "50%": { borderColor: "#3b82f6" } },
      },
      animation: {
        "accordion-down":  "accordion-down 0.2s ease-out",
        "accordion-up":    "accordion-up 0.2s ease-out",
        "fade-in":         "fade-in 0.2s ease-out",
        "slide-in-right":  "slide-in-right 0.25s ease-out",
        "slide-in-left":   "slide-in-left 0.25s ease-out",
        "pulse-dot":       "pulse-dot 2s ease-in-out infinite",
        "shimmer":         "shimmer 2s linear infinite",
        "blink-cursor":    "blink-cursor 1s step-end infinite",
      },
      backgroundImage: {
        "mesh-gradient": `
          radial-gradient(ellipse 900px 600px at 15% 0%, rgba(59,130,246,0.05) 0%, transparent 70%),
          radial-gradient(ellipse 700px 500px at 85% 100%, rgba(34,197,94,0.04) 0%, transparent 70%)
        `,
        "shimmer-gradient":
          "linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.04) 50%, transparent 75%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
