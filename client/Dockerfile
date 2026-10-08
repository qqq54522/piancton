ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine

FROM ${NODE_BASE_IMAGE} AS build
ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
ARG VITE_FEISHU_APP_ID=
ARG VITE_FEISHU_H5_SDK_URL=https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.16.js
ARG VITE_SELF_REGISTRATION_ENABLED=false
ENV VITE_FEISHU_APP_ID=${VITE_FEISHU_APP_ID}
ENV VITE_FEISHU_H5_SDK_URL=${VITE_FEISHU_H5_SDK_URL}
ENV VITE_SELF_REGISTRATION_ENABLED=${VITE_SELF_REGISTRATION_ENABLED}
WORKDIR /workspace/client
COPY client/package*.json ./
RUN npm ci --no-audit --no-fund --registry="${NPM_CONFIG_REGISTRY}"
COPY client .
RUN npm run build

FROM ${NGINX_BASE_IMAGE}
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/client/dist /usr/share/nginx/html
EXPOSE 80
