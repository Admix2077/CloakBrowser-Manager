import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#f8fafc",
          1: "#ffffff",
          2: "#f8fafc",
          3: "#eef6ff",
          4: "#e2e8f0",
        },
        border: {
          DEFAULT: "#e2e8f0",
          hover: "#cbd5e1",
        },
        accent: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
        },
      },
      boxShadow: {
        panel: "0 14px 32px rgba(15, 23, 42, 0.07)",
        hairline: "0 1px 2px rgba(15, 23, 42, 0.05)",
      },
    },
  },
  plugins: [],
} satisfies Config;
