FROM node:18
WORKDIR /app

# Copy package.json first (so Docker caches npm install step well)
COPY package.json ./

# If you have package-lock.json, uncomment the following line:
# COPY package-lock.json ./

# Install dependencies
RUN npm install --no-fund --no-audit --silent

# Copy remaining app files
COPY . .

# Default dev command (Vite)
CMD ["npm", "run", "dev", "--", "--host"]
