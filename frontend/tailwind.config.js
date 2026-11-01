/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B0E14",
        surface: "#F7F7F5",
        panel: "#FFFFFF",
        line: "#E7E5DF",
        muted: "#6B7280",
        rise: "#16794F",
        fall: "#B3261E",
        attention: {
          normal: "#9CA3AF",
          low: "#8AA6C2",
          moderate: "#D9A441",
          high: "#D96E2C",
          critical: "#B3261E",
        },
      },
      fontFamily: {
        display: ["'IBM Plex Serif'", "Georgia", "serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(11,14,20,0.04), 0 1px 1px rgba(11,14,20,0.03)",
      },
      keyframes: {
        pulseRing: {
          "0%": { transform: "scale(0.9)", opacity: "0.6" },
          "70%": { transform: "scale(1.6)", opacity: "0" },
          "100%": { transform: "scale(1.6)", opacity: "0" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseRing: "pulseRing 2.2s ease-out infinite",
        fadeUp: "fadeUp 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
