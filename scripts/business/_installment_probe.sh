#!/usr/bin/env bash
# 查 CN 现有 分期/对公/大额收款 能力 (¥899 大额怎么真收进来)
echo "=== 1. 系统里有没有 分期/对公/大额 收款机制 (代码) ==="
grep -rniE "分期|installment|split.*pay|对公|bank.*transfer|bank_transfer|corporate|大额|large.*order|batch.*pay|periodic|recurring|订阅扣款|autopay" /opt/bingdashan /www/wwwroot/tools-cn.highkingflower.com 2>/dev/null | grep -viE "node_modules|\.git|i18n|\.out|test" | head -15
echo ""
echo "=== 2. 收款渠道: 微信/支付宝/银行 现配了哪些 (对公码) ==="
grep -rhoE "^(PAYMENT_|WECHAT_|ALIPAY_[A-Z_]*|BANK_|CORP)[A-Z_]*" /etc/bingdashan-cn.env 2>/dev/null | sort -u | head
echo "  --- CN 收款渠道端点 (pay/channels) ---"
curl -sk --max-time 15 "https://tools-cn.highkingflower.com/v1/pay/channels" 2>/dev/null | head -c 400; echo
echo ""
echo "=== 3. alipay 网关是否支持商户侧分期 (alipay.trade.page.pay 的 installments 参数) ==="
# 支付宝 page.pay 有 installments 但通常是'客户端选分期', 商户侧不能强制拆账
grep -niE "installment|分期|period.*pay|royalty" /www/wwwroot/tools-cn.highkingflower.com/api/alipay.js 2>/dev/null | head
echo "  (alipay.js 里有没有分期/分账逻辑)"
echo ""
echo "=== 4. 微信收款码/对公码 配置 (大额线下打款的核账方式) ==="
grep -rniE "wechat.*qr|wx.*pay.*code|对公|bank.*code|打款|核销|write.?off|人工.*核|confirm.*receipt|pay.*confirm" /opt/bingdashan /www/wwwroot/tools-cn.highkingflower.com/api 2>/dev/null | grep -viE "node_modules|test|i18n" | head -12
echo "=== 5. 现有'打款待核销'队列 (大额线下打款的台账在哪) ==="
ls -1 /opt/bingdashan/data/billing/ 2>/dev/null | grep -iE "bank|corporate|large|install|manual|receipt|pending"
grep -rniE "打款|bank.*receipt|对公.*到账|corporate.*receipt" /opt/bingdashan/data/billing/*.jsonl 2>/dev/null | head -5
echo done
