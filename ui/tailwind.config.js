import daisyui from "daisyui"

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./ui/templates/**/*.html",
    "./ui/static/**/*."
  ],
  theme: {
    extend: {},
  },
  daisyui: {
    themes: [
      "light",
      "dark",
      "dracula",
      "wireframe",
    ]
  },
  plugins: [daisyui],
}

