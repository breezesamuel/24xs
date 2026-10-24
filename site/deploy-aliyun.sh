#!/bin/bash
# 阿里云一键部署脚本：在目标服务器上运行
# 用法：curl -sSL https://raw.githubusercontent.com/breezesamuel/24xs/main/deploy-aliyun.sh | bash -s -- <registry_password>
# 或下载后：bash deploy-aliyun.sh <registry_password>

set -e

REGISTRY="registry.cn-hangzhou.aliyuncs.com"
NAMESPACE="bingdashan"
IMAGE="bingdashan"
TAG="latest"
FULL_IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE}:${TAG}"

echo "=== bingdashan 阿里云部署 ==="
echo "镜像: ${FULL_IMAGE}"

# 1. 安装 Docker（如果没装）
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker && systemctl start docker
fi

# 2. 登录阿里云镜像仓库
if [ -n "$1" ]; then
    echo "登录镜像仓库..."
    docker login --username=bingdashan --password="$1" ${REGISTRY}
else
    echo "请提供镜像仓库密码：bash deploy-aliyun.sh <password>"
    exit 1
fi

# 3. 拉取最新镜像
echo "拉取镜像..."
docker pull ${FULL_IMAGE}

# 4. 创建环境变量文件（从 Vercel 同步或手动填）
ENV_FILE="/etc/bingdashan.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" <<'EOF'
# 填入你的实际值（从 Vercel 环境变量复制）
ALIPAY_APP_ID=
ALIPAY_MERCHANT_PRIVATE_KEY=
ALIPAY_ALIPAY_PUBLIC_KEY=
ALIPAY_AES_KEY=
ALIPAY_ACCOUNT=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
KV_REST_API_URL=
KV_REST_API_TOKEN=
COMMISSION_PCT=30
ADMIN_SECRET=
AUTOOPS_SECRET=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_TRIAL=
STRIPE_PRICE_PRO=
STRIPE_PRICE_PRO3=
STRIPE_PRICE_PROY=
STRIPE_PRICE_TEAM=
ARCADE_FREE_SEC=600
EOF
    echo "已创建 $ENV_FILE，请编辑填入真实值"
    exit 1
fi

# 5. 加载环境变量
set -a
source "$ENV_FILE"
set +a

# 6. 部署 systemd 服务
cat > /etc/systemd/system/bingdashan.service <<EOF
[Unit]
Description=bingdashan AI Tools Platform
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker stop bingdashan
ExecStartPre=-/usr/bin/docker rm bingdashan
ExecStart=/usr/bin/docker run --rm --name bingdashan \
  -p 80:80 -p 443:443 \
  -e ALIPAY_APP_ID=\${ALIPAY_APP_ID} \
  -e ALIPAY_MERCHANT_PRIVATE_KEY=\${ALIPAY_MERCHANT_PRIVATE_KEY} \
  -e ALIPAY_ALIPAY_PUBLIC_KEY=\${ALIPAY_ALIPAY_PUBLIC_KEY} \
  -e ALIPAY_AES_KEY=\${ALIPAY_AES_KEY} \
  -e ALIPAY_ACCOUNT=\${ALIPAY_ACCOUNT} \
  -e SUPABASE_URL=\${SUPABASE_URL} \
  -e SUPABASE_SERVICE_KEY=\${SUPABASE_SERVICE_KEY} \
  -e KV_REST_API_URL=\${KV_REST_API_URL} \
  -e KV_REST_API_TOKEN=\${KV_REST_API_TOKEN} \
  -e COMMISSION_PCT=\${COMMISSION_PCT} \
  -e ADMIN_SECRET=\${ADMIN_SECRET} \
  -e AUTOOPS_SECRET=\${AUTOOPS_SECRET} \
  -e STRIPE_SECRET_KEY=\${STRIPE_SECRET_KEY} \
  -e STRIPE_WEBHOOK_SECRET=\${STRIPE_WEBHOOK_SECRET} \
  -e STRIPE_PRICE_TRIAL=\${STRIPE_PRICE_TRIAL} \
  -e STRIPE_PRICE_PRO=\${STRIPE_PRICE_PRO} \
  -e STRIPE_PRICE_PRO3=\${STRIPE_PRICE_PRO3} \
  -e STRIPE_PRICE_PROY=\${STRIPE_PRICE_PROY} \
  -e STRIPE_PRICE_TEAM=\${STRIPE_PRICE_TEAM} \
  -e ARCADE_FREE_SEC=\${ARCADE_FREE_SEC} \
  ${FULL_IMAGE}
ExecStop=/usr/bin/docker stop bingdashan

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
systemctl daemon-reload
systemctl enable bingdashan
systemctl restart bingdashan

# 8. 安装 certbot 自动 HTTPS
if ! command -v certbot &> /dev/null; then
    apt-get update && apt-get install -y certbot
fi

echo "=== 部署完成 ==="
echo "服务状态: systemctl status bingdashan"
echo "日志: journalctl -u bingdashan -f"
echo "配置 HTTPS: certbot --nginx -d bingdashan.highkingflower.com"