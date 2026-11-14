#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const k=["keccak256","keccak","secp256k1GetPublicKey","secp256k1Verify","sha256"];
k.forEach(x=>console.log("  "+x+": "+(typeof viem[x])));
// 看 viem 里有没有 secp256k1 模块导出
console.log("  has secp256k1 keys:", Object.keys(viem).filter(x=>/secp|key|address/i.test(x)).join(", "));
'
