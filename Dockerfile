# Build the Vue app, then hand the static files to nginx.
FROM node:22-alpine AS build
WORKDIR /app
# Override these to serve under a subpath (e.g. behind a /demos/<slug>/ proxy).
ARG VITE_BASE=/
ARG VITE_API_BASE=/capi
ENV VITE_BASE=$VITE_BASE
ENV VITE_API_BASE=$VITE_API_BASE
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
