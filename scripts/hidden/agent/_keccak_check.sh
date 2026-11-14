#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
// keccak256 输入 64 字节, 看返回类型
const input=Buffer.alloc(64,0x01);
const out=viem.keccak256(input);
console.log("  keccak256 返回类型: "+typeof out+"  值前缀: "+String(out).slice(0,10)+"...  长度: "+String(out).length);
// 若是 0x 前缀 hex 串 (66 字符) -> 正确用法: 取 12.. 字符 (跳过 0x + 前 12 hex = 12 字节)
const hexOut=String(out);
if(hexOut.startsWith("0x") && hexOut.length===66){
  const addr="0x"+hexOut.slice(26); // 0x(2)+前12字节(24hex) 去掉 -> 后 20 字节
  console.log("  正确地址 = 0x"+hexOut.slice(26)+"  (len "+(2+hexOut.length-26)+")");
}
' 2>&1 | head -5
