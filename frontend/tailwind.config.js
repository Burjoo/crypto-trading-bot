/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Dark terminal palette
        bg: {
          primary:   "#0a0e1a",
          secondary: "#0f1629",
          card:      "#111827",
          elevated:  "#1a2235",
          border:    "#1e2d45",
        },
        accent: {
          cyan:    "#00d4ff",
          green:   "#00ff87",
          red:     "#ff3b6b",
          yellow:  "#ffd900",
          purple:  "#a855f7",
          orange:  "#ff7c2a",
        },
        text: {
          primary:   "#e8f0fe",
          secondary: "#8899aa",
          muted:     "#4a6070",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono:    ["'JetBrains Mono'", "'Fira Code'", "monospace"],
        body:    ["'Inter'", "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        "glow-cyan":   "0 0 20px rgba(0,212,255,0.15), 0 0 40px rgba(0,212,255,0.05)",
        "glow-green":  "0 0 20px rgba(0,255,135,0.15), 0 0 40px rgba(0,255,135,0.05)",
        "glow-red":    "0 0 20px rgba(255,59,107,0.15)",
        "card":        "0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
      },
      backgroundImage: {
        "grid-pattern": "linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)",
        "gradient-card": "linear-gradient(135deg, rgba(17,24,39,0.9) 0%, rgba(26,34,53,0.9) 100%)",
      },
      backgroundSize: {
        "grid": "40px 40px",
      },
      animation: {
        "pulse-slow":   "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-in":     "slideIn 0.2s ease-out",
        "fade-in":      "fadeIn 0.3s ease-out",
        "ticker":       "ticker 30s linear infinite",
        "glow":         "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        slideIn: {
          "0%":   { transform: "translateY(-8px)", opacity: "0" },
          "100%": { transform: "translateY(0)",    opacity: "1" },
        },
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        ticker: {
          "0%":   { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        glow: {
          "0%":   { boxShadow: "0 0 5px rgba(0,212,255,0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(0,212,255,0.5)" },
        },
      },
    },
  },
  plugins: [],
};
