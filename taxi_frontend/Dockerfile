# Build the React app, then serve the static files with nginx.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY public ./public
COPY src ./src
ARG REACT_APP_API_URL=http://localhost:8000/api
ARG REACT_APP_DASHBOARD_URL=http://localhost:8050
ARG REACT_APP_GOOGLE_MAPS_API_KEY=
ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_DASHBOARD_URL=$REACT_APP_DASHBOARD_URL \
    REACT_APP_GOOGLE_MAPS_API_KEY=$REACT_APP_GOOGLE_MAPS_API_KEY
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
