FROM node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM dependencies AS builder
COPY . .
ARG NEXT_PUBLIC_AUTH_API_URL=/api/auth
ARG NEXT_PUBLIC_TASK_API_URL=/api/task
ENV NEXT_PUBLIC_AUTH_API_URL=$NEXT_PUBLIC_AUTH_API_URL NEXT_PUBLIC_TASK_API_URL=$NEXT_PUBLIC_TASK_API_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run lint && npm run build && node docker/prepare-runtime.cjs

FROM node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public
COPY --chown=node:node docker/start.cjs ./docker/start.cjs
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "docker/start.cjs"]
