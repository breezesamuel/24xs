#!/usr/bin/env bash
echo "=== /opt/bingdashan 结构 (真生产系统) ==="
ls -1 /opt/bingdashan/data/runtime/ 2>/dev/null | head -20
echo "=== reconcile_latest.json (对账最新结果, 含 paid/pending 口径) ==="
cat /opt/bingdashan/data/runtime/reconcile_latest.json 2>/dev/null | head -c 1500; echo
echo "=== pay-watch 目录 (待付监控) ==="
ls -1 /opt/bingdashan/pay-watch/ 2>/dev/null | head -20
echo "=== 找订单账本 (pending 订单数据) ==="
find /opt/bingdashan -maxdepth 4 -type f \( -iname '*order*' -o -iname '*pending*' -o -iname '*reconcile*' \) 2>/dev/null | grep -vE 'node_modules' | head -20
