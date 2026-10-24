# AI 自动化平台 ECS 部署档案（2026-10-25）
- 源码：F:/24小时/ai-automation-platform → /opt/ai-auto（venv=python3.11）
- 服务：aiauto.service，uvicorn src.api.main:app，127.0.0.1:8890，MemoryMax 300M，Restart=always
- 公网：https://bingdashanai.highkingflower.com/agents/ （vhost 01-bingdashanai-ssl.conf，location /agents/ → 8890/）
- 健康含支付状态（fail-closed：ALIPAY_* 未配即 real_payments_ready=false，如实上报）
- SSH：ssh -i ~/.ssh/solomount_ecs_ed25519 root@8.155.53.12
- 注意：8792/8793 已被其他服务占用，选定 8890；nginx 为宝塔布局 /www/server/nginx
