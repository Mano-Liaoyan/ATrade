# Image of the Compose service `assistant`: the Node.js process with the pi SDK and the Claude Agent SDK
# (docs/architecture/assistant.md 25.2, 25.7.5).
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
# The official, unmodified `claude` binary of the Claude Agent SDK (docs/architecture/assistant.md 25.7.5). The SDK
# starts it from node_modules. The link puts it on PATH for the one-time login:
#   docker compose --file deploy/compose.yaml --env-file .env exec assistant claude auth login
RUN claude_binary="$(find /app/node_modules/.pnpm -path '*/@anthropic-ai/claude-agent-sdk-linux-*/claude' -not -path '*musl*' -type f | head -n 1)" \
    && test -n "$claude_binary" \
    && ln -s "$claude_binary" /usr/local/bin/claude
# /data is the volume atrade-assistant-pi. A new volume takes the owner of this directory.
RUN mkdir /data && chown node:node /data
USER node
# The root file system is read-only at run time. Only /data and /tmp are writable.
ENV HOME=/data NODE_ENV=production
CMD ["node", "src/main.ts"]
