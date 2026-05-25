import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#f6f8fb",
          1: "#ffffff",
          2: "#f8fafc",
          3: "#eff6ff",
          4: "#e2e8f0",
        },
        border: {
          DEFAULT: "#dbe3ef",
          hover: "#aebed2",
        },
        accent: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
        },
      },
      boxShadow: {
        panel: "0 18px 45px rgba(15, 23, 42, 0.08)",
        hairline: "0 1px 2px rgba(15, 23, 42, 0.05)",
      },
    },
  },
  plugins: [],
} satisfies Config;
