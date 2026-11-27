FROM node:26-slim

WORKDIR /app
RUN chown node:node /app
USER node

# Dependencies first, in their own layer: source edits do not reinstall them (R15).
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

COPY --chown=node:node . .
RUN npm run build

EXPOSE 5173

# vite preview serves dist/ and proxies /api to API_PROXY_TARGET (set by compose).
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
