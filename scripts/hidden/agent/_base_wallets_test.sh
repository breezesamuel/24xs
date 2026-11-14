#!/usr/bin/env bash
# 验 Base 体系: 新钱包在 config + 结算到 base_receive / agentpay_treasury + 红线仍拒 unowned
B="https://tools-cn.highkingflower.com/api"
echo "=== config 含 Base 体系钱包? ==="
curl -sk "$B/config" --max-time 25 | python -c "import sys,json;w=json.load(sys.stdin).get('wallets',{});print('  base_receive:', '0x74a9f91763c28571af7a52987f425f62825cf5d8' in json.dumps(w));print('  agentpay_treasury:', '0x367F1b3D8Ca90D1e087481a9A40d585Bf3451a03' in json.dumps(w));print('  base_usdc_contract:', '0x833589fCD2e695B55A1C68A696f0810f2C3AD36C' in json.dumps(w))" 2>&1 | head -4
echo "=== (a) 结算到 base_receive (earned, 合法) ==="
curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":100,"asset":"USDC","source":"earned","dest":"base_receive"}' | head -c 240; echo
echo "=== (b) 结算到 agentpay_treasury (earned, 合法) ==="
curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":50,"asset":"USDC","source":"earned","dest":"agentpay_treasury"}' | head -c 240; echo
echo "=== (c) 红线: unowned -> 仍拒 ==="
curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":5000,"asset":"USDT","source":"unowned","dest":"base_receive"}' | head -c 160; echo
echo "=== (d) 打合约 (base_usdc_contract) -> 应拒 (is_contract) ==="
curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":10,"asset":"USDC","source":"earned","dest":"base_usdc_contract"}' | head -c 160; echo
echo "=== 清理本测试结算单 ==="
rm -f /var/lib/bingdashan-cn/coinsettle_CS_demo_user_a_*.json 2>/dev/null
echo done
