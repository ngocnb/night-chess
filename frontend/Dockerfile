# Stage 1: deps — install Node dependencies
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: development — hot reload via volume mounts
FROM deps AS development

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

# Stage 3: builder — produce optimised production build
FROM deps AS builder

COPY . .

RUN npm run build

# Stage 4: runtime — minimal production image (Next.js standalone)
FROM node:20-alpine AS runtime

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy public assets
COPY --from=builder /app/public ./public

# Copy Next.js standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
