#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
WORK=$(mktemp -d /tmp/_dbg.XXXX)
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/key.pem" 2>/dev/null
openssl ec -in "$WORK/key.pem" -text -noout 2>/dev/null > "$WORK/_text.txt"
cat "$WORK/_text.txt"
rm -rf "$WORK"
