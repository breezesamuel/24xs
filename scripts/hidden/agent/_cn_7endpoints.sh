#!/usr/bin/env bash
for e in "bounty?action=tasks" "cashback?action=rate" "writerewards?action=rate" "charity?action=total" "bandwidth?action=rate" "recovery?action=rate" "config"; do
  printf "  %s: " "$e"
  curl -sk "https://tools-cn.highkingflower.com/api/$e" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
done
echo "channels.html:"
curl -sk "https://tools-cn.highkingflower.com/channels.html" -o /dev/null -w "  HTTP %{http_code} size=%{size_download}\n" --max-time 20
