# Image of the Compose service `assistant`: the Node.js process with the pi SDK (docs/architecture/assistant.md 25.2).
# Build context: the repository root (see deploy/compose.yaml).

# The Vite+ image runs as the user vp in /app. It installs only the production dependencies.
FROM ghcr.io/voidzero-dev/vite-plus:1.4.0 AS dependencies
WORKDIR /app
COPY --chown=vp:vp assistant/package.json assistant/pnpm-lock.yaml assistant/pnpm-workspace.yaml assistant/.node-version ./
RUN vp install --frozen-lockfile --prod

# Node.js runs the TypeScript files directly (type stripping), so there is no build step.
FROM node:24.13.0-slim AS assistant
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY assistant/package.json ./
COPY assistant/src ./src
# /data is the volume atrade-assistant-pi. A new volume takes the owner of this directory.
RUN mkdir /data && chown node:node /data
USER node
# The root file system is read-only at run time. Only /data and /tmp are writable.
ENV HOME=/data NODE_ENV=production
CMD ["node", "src/main.ts"]
