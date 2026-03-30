# /grimoire-ux/Dockerfile (Frontend)
# --- STAGE 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

# Copia os ficheiros de dependências primeiro (aproveita cache do Docker)
COPY package.json package-lock.json ./
RUN npm ci

# Copia o resto do código e compila (Tailwind v4 + Vite)
COPY . .
# Se houver variáveis de ambiente estáticas para o frontend, passe-as aqui
RUN npm run build

# --- STAGE 2: Produção (Nginx) ---
FROM nginx:alpine

# Remove o index padrão do Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia o build final do React para a pasta do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a nossa configuração customizada
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
