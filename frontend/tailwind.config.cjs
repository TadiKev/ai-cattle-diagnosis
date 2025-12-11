/** @type {import("tailwindcss").Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          500: "#16a34a",
          600: "#15803d"
        }
      }
    }
  },
  plugins: [],
};
