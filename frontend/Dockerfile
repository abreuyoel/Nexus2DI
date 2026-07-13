# syntax=docker/dockerfile:1
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build:prod


# Usuario no-root, escucha en 8080 (no 80) — permite runAsNonRoot en el pod
# sin trucos adicionales de puertos privilegiados.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS production
COPY --from=build /app/dist/epran-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
