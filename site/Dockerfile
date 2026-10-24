# 多阶段构建：Vercel 静态输出 -> nginx 运行时
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production 2>/dev/null || npm install --only=production
COPY . .
# 生成 Vercel 输出目录结构
RUN mkdir -p /app/.vercel/output/static /app/.vercel/output/functions/api
# 复制静态文件
RUN cp -r *.html *.css *.js *.png *.ico *.svg *.txt *.xml *.json *.webmanifest /app/.vercel/output/static/ 2>/dev/null || true
RUN cp -r arcade /app/.vercel/output/static/ 2>/dev/null || true
RUN cp -r exam resume freelance creator boss parent seller office spender sitter insomnia gift elderkids rest coffee stack housewife pet cross homeowner housebuyer renter backpack traveler commuter newparents ev gas social peopleplease wedding examcert study roommate looking hoarder blinddate pressured guitar photofresh paperwork worker streetstall gymnew /app/.vercel/output/static/ 2>/dev/null || true
# API 函数打包（Vercel Node.js runtime 兼容）
RUN for f in api/*.js; do \
      fn=$(basename $f .js); \
      mkdir -p /app/.vercel/output/functions/api/$fn; \
      cp $f /app/.vercel/output/functions/api/$fn/func.js; \
      echo '{"runtime":"nodejs20.x","handler":"func.module.exports"}' > /app/.vercel/output/functions/api/$fn/.vc-config.json; \
    done

# 运行时：nginx + nodejs 代理
FROM nginx:alpine
# 安装 nodejs 运行 API
RUN apk add --no-cache nodejs npm
# 复制构建产物
COPY --from=builder /app/.vercel/output /app
# nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf
# 启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh
EXPOSE 80 443
CMD ["/start.sh"]