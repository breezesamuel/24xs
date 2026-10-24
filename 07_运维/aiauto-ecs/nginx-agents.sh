#!/bin/bash
set -e
F=/www/server/panel/vhost/nginx/01-bingdashanai-ssl.conf
if grep -q 'location /agents/' "$F"; then echo "already present"; exit 0; fi
cat > /tmp/agents.loc <<'BLOCK'
    location /agents/ {
        proxy_pass http://127.0.0.1:8890/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

BLOCK
awk 'BEGIN{d=0} /location \/ \{/ && d==0 { while((getline l < "/tmp/agents.loc")>0) print l; d=1 } {print}' "$F" > "$F.new"
cp "$F" "$F.bak"
mv "$F.new" "$F"
nginx -t 2>&1 | tail -1
nginx -s reload
echo RELOADED
