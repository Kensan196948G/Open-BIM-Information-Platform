FROM node:22.22.0-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30.4-alpine@sha256:45ce1e2e699234253d1def7baa96218a5d00b498d1ba0cbb1a17b6bdf73d1351

ARG NGINX_RUNTIME_UID=1000
ARG NGINX_RUNTIME_GID=1000

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Match this numeric identity to the owner of the mode-0600 TLS key on the host.
USER ${NGINX_RUNTIME_UID}:${NGINX_RUNTIME_GID}
EXPOSE 8080 8443

# Skip image entrypoint mutation; the runtime filesystem is intentionally read-only.
ENTRYPOINT ["nginx", "-g", "daemon off;"]
