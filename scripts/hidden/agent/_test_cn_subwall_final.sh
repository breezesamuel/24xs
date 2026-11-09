#!/bin/bash
WEBROOT=/www/wwwroot/tools-cn.highkingflower.com
# 用服务的真实 env (含 FILE_STORE_DIR) 计算路径 + seed
cd "$WEBROOT"
set -a; source /etc/bingdashan-cn.env; set +a
REF="cnok_$(date +%s)"
REALPATH=$(node -e "
const key='subwall:'+('$REF');
const safe=String(key).replace(/[^A-Za-z0-9_.:-]/g,'_').slice(0,180);
console.log(process.env.FILE_STORE_DIR+'/'+safe+'.json');
")
echo "FILE_STORE_DIR=[$(node -e 'console.log(process.env.FILE_STORE_DIR)')]"
echo "seed 路径: $REALPATH"
NOW=$(date +%s%3N)
echo "[{\"plan\":\"pro\",\"status\":\"active\",\"since\":${NOW},\"expires\":$((NOW+31*86400000)),\"paid_out\":\"CNOK\"}]" > "$REALPATH"
ls -la "$REALPATH" 2>&1

echo "=== HTTP 读回 (新版 file fallback, 进程已重启) ==="
curl -s -X POST "https://tools-cn.highkingflower.com/api/subwall" \
  -H "Content-Type: application/json" -d "{\"action\":\"check\",\"ref\":\"$REF\"}" --max-time 20
echo
rm -f "$REALPATH"
echo "(seed 已清理)"
