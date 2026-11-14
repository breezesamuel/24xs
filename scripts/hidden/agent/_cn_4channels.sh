#!/usr/bin/env bash
# CN 4 渠道端点全确认 (bounty/cashback/writerewards + 支付宝 config)
for e in "bounty?action=tasks" "cashback?action=rate" "writerewards?action=rate" "config"; do
  printf "%s: " "$e"
  curl -sk "https://tools-cn.highkingflower.com/api/$e" --max-time 15 -o /dev/null -w "HTTP %{http_code}\n"
done
echo "--- bounty ?a=claim 无 ref (fail-closed 400/403) ---"
curl -sk "https://tools-cn.highkingflower.com/api/bounty?action=claim&task_id=by_introduce&proof=x" --max-time 15 | head -c 80
echo ""
