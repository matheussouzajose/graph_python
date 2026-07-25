# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1: Builder - install dependencies and compile the Vite app
# =============================================================================
FROM node:24-alpine AS builder

ARG NPM_VERSION=11.6.2
RUN npm install -g npm@${NPM_VERSION}

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# =============================================================================
# Stage 2: Runtime - serve static assets behind Traefik
# =============================================================================
FROM node:24-alpine AS runtime

ARG NPM_VERSION=11.6.2
RUN npm install -g npm@${NPM_VERSION} serve@14.2.5 \
    && addgroup -S appgroup \
    && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/dist ./dist

USER appuser

EXPOSE 4173

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:4173 || exit 1

CMD ["serve", "-s", "dist", "-l", "4173"]
pq vou fazer 