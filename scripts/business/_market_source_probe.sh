#!/usr/bin/env bash
# 路线2前置: CN 有没有可用公开 K 线数据源 (回测要喂真数据)
echo "=== 1. CN 站点/系统里有没有现成行情/K线数据 (本地缓存/数据源) ==="
find /opt/bingdashan /www/wwwroot/tools-cn.highkingflower.com -maxdepth 4 -iname "*.csv" -o -iname "*kline*" -o -iname "*candle*" -o -iname "*ohlcv*" 2>/dev/null | grep -viE "node_modules|\.git" | head -12
echo ""
echo "=== 2. 有没有行情 API 客户端 (akshare/tushare/公开REST) 可用 ==="
which python3 python3.11 2>/dev/null
python3 -c "import akshare" 2>/dev/null && echo "  akshare 已装" || echo "  akshare 未装"
python3 -c "import tushare" 2>/dev/null && echo "  tushare 已装" || echo "  tushare 未装"
echo ""
echo "=== 3. 公网行情 API 连通性 (CN 能直连哪个公开 K 线源) ==="
for u in "https://api.alpaca.markets/v2" "https://query1.finance.yahoo.com" "https://api.coingecko.com/api/v3" "https://data-api.binance.vision/api/v3/klines"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 8 "$u" 2>/dev/null)
  echo "  $u -> HTTP $code"
done
echo ""
echo "=== 4. CN 网络: 能否访问币安公开K线 (最稳的公开行情, 免费无key) ==="
curl -sk --max-time 10 "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=3" 2>/dev/null | head -c 300; echo
echo done
