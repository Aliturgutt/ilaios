FROM node:22.23.1-bookworm-slim@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3

ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_MCP_BROWSER=chromium

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --global --omit=dev @playwright/cli@0.1.17 \
    && PW_ROOT="$(npm root --global)/@playwright/cli" \
    && node "$PW_ROOT/node_modules/playwright/cli.js" install --with-deps chromium \
    && playwright-cli --help >/dev/null \
    && chmod -R a+rX "$PLAYWRIGHT_BROWSERS_PATH" \
    && npm cache clean --force \
    && rm -rf /root/.npm

USER node
WORKDIR /workspace

CMD ["sleep", "infinity"]
