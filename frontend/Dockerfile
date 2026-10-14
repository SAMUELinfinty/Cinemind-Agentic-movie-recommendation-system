# Build the Vite SPA, then serve it with nginx.
# VITE_API_URL is baked in at build time: set it as a Railway variable
# (e.g. VITE_API_URL=https://<api>.up.railway.app).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
ARG VITE_API_URL=http://localhost:5000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# The official nginx image renders /etc/nginx/templates/*.template with
# envsubst on startup, so $PORT (injected by Railway) just works.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
CMD ["nginx", "-g", "daemon off;"]
