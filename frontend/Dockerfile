ARG BUN_VERSION=1.3.10

FROM oven/bun:${BUN_VERSION} AS deps

LABEL maintainer="Voyage contributors" \
      version="v0.12.0" \
      description="Voyage — the ultimate self-hosted travel companion." \
      org.opencontainers.image.title="Voyage" \
      org.opencontainers.image.description="Voyage is a self-hosted travel companion that helps you plan, track, and share your adventures." \
      org.opencontainers.image.version="v0.12.0" \
      org.opencontainers.image.authors="Voyage contributors" \
      org.opencontainers.image.url="https://voyage.app" \
      org.opencontainers.image.source="https://github.com/Alex-Wiesner/voyage" \
      org.opencontainers.image.vendor="Voyage contributors" \
      org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

FROM deps AS builder

COPY . .
RUN rm -f .env \
    && bun run build

FROM oven/bun:${BUN_VERSION} AS prod-deps

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --production

FROM gcr.io/distroless/nodejs22-debian12:nonroot AS runtime

WORKDIR /app

COPY --from=builder /app/build ./build
COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["build/index.js"]
