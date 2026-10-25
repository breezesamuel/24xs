// GET /pay/cancel - PayPal cancel page
export default function handler(req, res) {
  const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>已取消</title>
<style>body{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto;padding:0 16px;line-height:1.6}
.card{border:1px solid #e5e7eb;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.warn{color:#d97706}</style></head>
<body><div class="card">
<h2 class="warn">⚠️ 买家取消了付款</h2>
<p>未产生任何扣款，订阅未激活。</p>
<p>可重新点击看板上的套餐按钮发起新的支付流程。</p>
</div></body></html>`;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.send(html);
}