#!/usr/bin/env bash
# 一键部署到国内服务器（Alibaba Cloud Linux / CentOS / Ubuntu 通用）。
#
# 为什么必须有这一步：
#   *.vercel.app 在中国大陆被 DNS 污染 + IP 封锁。后果不是"网站慢"，而是：
#     1) 上海的客户根本打不开官网
#     2) **支付宝的异步通知也打不进来** —— 客户付了钱，系统永远收不到确认
#   收款链路放在国内服务器才成立。
#
# 前置：本机已把公钥写进服务器的 ~/.ssh/authorized_keys
# 用法：bash deploy.sh <user>@<host>
set -euo pipefail

TARGET="${1:?用法: bash deploy.sh user@host}"
REMOTE_DIR="${GEO_DIR:-/opt/geoaudit}"
PORT="${GEO_PORT:-8800}"
PUBLIC_URL="${GEO_PUBLIC_URL:-}"

echo "==> 目标: $TARGET   目录: $REMOTE_DIR   端口: $PORT"

# ---- 1. 检查依赖 ----
echo "==> 检查目标机依赖"
ssh "$TARGET" 'set -e
  for b in python3 openssl nginx; do
    command -v $b >/dev/null 2>&1 && echo "  ok: $b" || echo "  MISSING: $b"
  done
  python3 -c "import sys;print(\"  python\",sys.version.split()[0])"
  openssl version | sed "s/^/  /"'

# ---- 2. 传代码 ----
echo "==> 上传代码"
ssh "$TARGET" "sudo mkdir -p $REMOTE_DIR/api $REMOTE_DIR/china"
# 只传需要的东西，别把 .venv / __pycache__ / 密钥一起端过去
scp -q 10_官网/index.html          "$TARGET:/tmp/_gi_index.html"
scp -q 10_官网/subscribe.html      "$TARGET:/tmp/_gi_sub.html"
scp -q 10_官网/robots.txt          "$TARGET:/tmp/_gi_robots.txt"
scp -q 10_官网/llms.txt            "$TARGET:/tmp/_gi_llms.txt"
scp -q 10_官网/sitemap.xml         "$TARGET:/tmp/_gi_sitemap.xml"
scp -q 10_官网/api/*.py            "$TARGET:/tmp/"
scp -q 10_官网/china/server.py     "$TARGET:/tmp/_gi_server.py"
ssh "$TARGET" "sudo cp /tmp/_gi_index.html $REMOTE_DIR/index.html
sudo cp /tmp/_gi_sub.html   $REMOTE_DIR/subscribe.html
sudo cp /tmp/_gi_robots.txt $REMOTE_DIR/robots.txt
sudo cp /tmp/_gi_llms.txt   $REMOTE_DIR/llms.txt
sudo cp /tmp/_gi_sitemap.xml $REMOTE_DIR/sitemap.xml
sudo cp /tmp/_gi_server.py  $REMOTE_DIR/china/server.py
sudo cp /tmp/*.py           $REMOTE_DIR/api/ 2>/dev/null || true
sudo rm -f /tmp/_gi_* /tmp/alipay_*.py /tmp/order.py /tmp/audit.py
sudo chown -R \$(whoami) $REMOTE_DIR 2>/dev/null || true
echo '  上传完成'"

# ---- 3. 环境变量（密钥不出现在命令行历史里）----
echo "==> 写入环境变量"
if [ -n "${ALIPAY_APP_ID:-}" ]; then
  ssh "$TARGET" "sudo mkdir -p $REMOTE_DIR && sudo tee $REMOTE_DIR/.env >/dev/null <<'ENVEOF'
GEO_HOST=127.0.0.1
GEO_PORT=$PORT
ALIPAY_APP_ID=$ALIPAY_APP_ID
ALIPAY_PRIVATE_KEY=$(printf '%s' "$ALIPAY_PRIVATE_KEY" | base64 -w0)
ALIPAY_PUBLIC_KEY=$(printf '%s' "$ALIPAY_PUBLIC_KEY" | base64 -w0)
ALIPAY_NOTIFY_URL=$ALIPAY_NOTIFY_URL
ALIPAY_RETURN_URL=$ALIPAY_RETURN_URL
ENVEOF
sudo chmod 600 $REMOTE_DIR/.env
echo '  .env 已写入 (600)'"
else
  echo "  !! 未提供 ALIPAY_APP_ID，跳过 .env（体检功能可用，收款不可用）"
fi

# ---- 4. systemd ----
echo "==> 注册 systemd 服务"
ssh "$TARGET" "sudo tee /etc/systemd/system/geoaudit.service >/dev/null <<'SVCEOF'
[Unit]
Description=GEO Audit (static site + Alipay + free site audit API)
After=network.target

[Service]
Type=simple
WorkingDirectory=$REMOTE_DIR
ExecStart=/usr/bin/env python3 $REMOTE_DIR/china/server.py
Environment=GEO_HOST=127.0.0.1
Environment=GEO_PORT=$PORT
EnvironmentFile=-$REMOTE_DIR/.env
Restart=always
RestartSec=3
# 体检要往外抓目标站，需要出网；不需要 root
User=\$(whoami)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$REMOTE_DIR /tmp

[Install]
WantedBy=multi-user.target
SVCEOF
sudo systemctl daemon-reload
sudo systemctl enable --now geoaudit
sleep 2
sudo systemctl is-active geoaudit && echo '  服务已启动'"

# ---- 5. nginx 反代 ----
echo "==> 配置 nginx"
ssh "$TARGET" "sudo tee /etc/nginx/conf.d/geoaudit.conf >/dev/null <<'NGXEOF'
# GEO 体检站点。注意：不碰已有的博鳌亚洲博览会站配置。
server {
    listen 80;
    server_name _;
    location / {
        root $REMOTE_DIR;
        try_files \$uri \$uri/ /index.html;
    }
}
server {
    listen 8800;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;   # 体检要抓外部站，可能慢
    }
}
NGXEOF
sudo nginx -t && sudo systemctl reload nginx && echo '  nginx 已生效'"

# ---- 6. 自检 ----
echo "==> 部署后自检"
sleep 1
for path in "/" "/robots.txt" "/llms.txt" "/subscribe.html"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "http://127.0.0.1:8800$path")
  printf '  %-16s %s\n' "$path" "$code"
done
echo -n "  SSRF 防护        "
curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 -X POST \
  "http://127.0.0.1:8800/api/audit" \
  -H 'Content-Type: application/json' -d '{"url":"http://169.254.169.254/"}'
echo -n "  真体检           "
curl -s --max-time 60 -X POST "http://127.0.0.1:8800/api/audit" \
  -H 'Content-Type: application/json' -d '{"url":"https://www.baidu.com"}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"score={d.get('score')} grade={d.get('grade')}\")" 2>/dev/null || echo "(超时)"

echo
echo "==> 完成。"
echo "    支付宝异步通知必须指向:  http://<你的域名>/api/alipay_notify"
echo "    该地址要在国内可被支付宝服务器访问，否则收不到到账确认。"
[ -n "$PUBLIC_URL" ] && echo "    公开地址: $PUBLIC_URL"