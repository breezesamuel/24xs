#!/usr/bin/env bash
# coinsettle preview (无密钥也回显): 确认 key_file 指向已存在的密钥 + 合规门
echo "=== CN coinsettle preview (key 已放, 应显示 key_file 存在 + live=false) ==="
curl -sk "https://tools-cn.highkingflower.com/api/coinsettle?preview=1" --max-time 25 > /tmp/_preview.json
python -c "
import json
d=json.load(open('/tmp/_preview.json'))
print('  live:', d.get('live'), '| chain:', d.get('payout_chain'), '| default_dest:', d.get('default_dest'))
print('  key_file:', d.get('key_file'))
import os
print('  key_file 存在:', os.path.exists(d.get('key_file','')))
print('  可用收款目标:', [x['key'] for x in d.get('valid_dests',[])])
"
echo "=== 确认密钥文件 (CN) ==="
ls -la /etc/coinsettle/payout_key 2>/dev/null | awk '{print "  "$1, $5, $9}'
echo done
