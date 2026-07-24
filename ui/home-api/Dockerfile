FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --production

FROM node:20-alpine
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /app/node_modules ./node_modules
COPY . .
RUN mkdir -p /app/data && chown -R app:app /app/data
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://localhost:3000/healthz || exit 1
CMD ["node", "server.js"]
