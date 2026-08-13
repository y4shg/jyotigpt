# JyotiGPT — all-in-one image
# Runs both the FastAPI backend (uvicorn, :8000) and the Next.js web server
# (next start, :3001) inside a single container. The web is the single origin
# the browser talks to; /api/* requests are proxied to the backend by Next's
# rewrite (see web/next.config.ts).
#
# Multi-stage:
#   stage 1 (web-build)  node:22-slim  -> npm ci + `next build`
#   stage 2 (runtime)    python:3.12-slim + Node 22 -> both apps + entrypoint

# ---- Stage 1: build the web bundle ---------------------------------------
FROM node:22-slim AS web-build

WORKDIR /app

# Install deps
COPY web/package.json web/package-lock.json ./
RUN npm ci

# Copy source and build
COPY web/ ./
RUN npm run build

# ---- Stage 2: runtime (Python 3.12 + Node 22) ----------------------------
FROM python:3.12-slim

WORKDIR /app

# System deps: compile deps for lxml/bcrypt + tooling to fetch the Node runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc libxml2-dev libxslt-dev \
      curl xz-utils ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Node 22 runtime via the official per-arch tarball. buildx sets TARGETARCH
# (amd64|arm64); nodejs.org uses linux-x64 / linux-arm64.
ARG TARGETARCH
RUN ARCH="$( [ "$TARGETARCH" = "amd64" ] && echo x64 || echo arm64 )" && \
    curl -fsSL -o /tmp/node.tar.xz \
      "https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-${ARCH}.tar.xz" && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz && \
    node --version && npm --version

# Install Python deps from pyproject (empty local package at this point, which
# is fine — the dependency resolution is what we need).
COPY api/pyproject.toml ./
RUN pip install --no-cache-dir .

# API source
COPY api/ ./api/

# Web build artifacts from stage 1
COPY --from=web-build /app/.next ./.next
COPY --from=web-build /app/node_modules ./node_modules
COPY --from=web-build /app/package.json ./
COPY --from=web-build /app/public ./public
COPY --from=web-build /app/next.config.ts ./

# Entrypoint starts both servers (see entrypoint.sh)
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 3001 8000

# Health check goes through the web origin (:3001) so it exercises the Next
# rewrite AND the backend together.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import httpx; httpx.get('http://localhost:3001/api/v1/config').raise_for_status()"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
