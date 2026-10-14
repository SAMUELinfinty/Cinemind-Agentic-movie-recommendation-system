FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY src ./src
ENV PORT=5000
EXPOSE 5000
CMD ["node", "src/server.js"]
