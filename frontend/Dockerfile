# Build-Stufe: React-App mit Node.js bauen
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./

RUN npm install

COPY . .

RUN npm run build


# Produktions-Stufe: React-App über Nginx ausliefern
FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
