ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine

FROM ${NODE_BASE_IMAGE} AS build
ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
WORKDIR /workspace/client
COPY client/package*.json ./
RUN npm ci --no-audit --no-fund --registry="${NPM_CONFIG_REGISTRY}"
COPY client .
RUN npm run build

FROM ${NGINX_BASE_IMAGE}
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/client/dist /usr/share/nginx/html
EXPOSE 80
