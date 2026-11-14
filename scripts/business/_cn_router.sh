#!/usr/bin/env bash
# 看 site_cn_server.mjs 怎么路由 /api/track (它怎么决定 track.js 服务哪些路由), 照加 /api/contact
echo "=== 1. site_cn_server.mjs 里 track / api 路由映射 ==="
grep -nE "track|api/track|rewrite|route|vercel|/api/|require\('\./api|api/track|track\.js" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs 2>/dev/null | grep -viE "\.bak|comment|//.*old" | head -30
echo ""
echo "=== 2. 它怎么读 vercel.json 的 rewrites ==="
grep -nE "vercel\.json|rewrites|destination|source" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs 2>/dev/null | head -20
echo ""
echo "=== 3. vercel.json 里 /api/track 的 rewrite (track.js) ==="
python -c "
import json
d=json.load(open('/www/wwwroot/tools-cn.highkingflower.com/vercel.json'))
for r in d.get('rewrites',[]):
    s=r.get('source','')
    if 'track' in s or 'contact' in s:
        print(' ', s, '->', r.get('destination'))
print('  含 api/track/contact 的 rewrite 数:', sum(1 for r in d.get('rewrites',[]) if 'track' in r.get('source','') or 'contact' in r.get('source','')))
"
echo done
