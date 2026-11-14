#!/usr/bin/env bash
DIR=/var/lib/bingdashan-cn
echo "=== 我们的结算单 (demo_user_a) 完整内容 ==="
cat "$DIR/coinsettle_CS_demo_user_a_MWC529KI.json" 2>/dev/null; echo
echo
echo "=== demo_user_a 币账本汇总 (bounty/writerewards 子目录) ==="
node - "$DIR" <<'NODE'
const fs=require('fs'),path=require('path');
const dir=process.argv[1];
function sum(subdir, ref){
  let files=[];try{files=fs.readdirSync(path.join(dir,subdir)).filter(x=>x.endsWith('.json'));}catch(e){return{files:0,entries:0,tokens:0,note:'no dir'};}
  let t=0,n=0;
  for(const f of files){
    try{
      const o=JSON.parse(fs.readFileSync(path.join(dir,subdir,f),'utf8'));
      // 结构可能是 {entries:[...]} 或 直接对象 / 数组; 只算属于该 ref 的
      let arr=[];
      if(Array.isArray(o)) arr=o;
      else if(o.entries) arr=o.entries;
      else if(o.items) arr=o.items;
      else if(o.ref) arr=[o];      // 单 ref 单文件
      arr=arr.filter(e=>!ref || !e.ref || e.ref===ref);
      n+=arr.length;
      for(const e of arr){ t+=(e.tokens||e.reward||0); }
    }catch(e){}
  }
  return {files:files.length,entries:n,tokens:t};
}
const b=sum('bounty','demo_user_a');
const w=sum('writerewards','demo_user_a');
console.log('  bounty  (demo_user_a): '+JSON.stringify(b));
console.log('  writing (demo_user_a): '+JSON.stringify(w));
console.log('  合计 earned 币: '+(b.tokens+w.tokens));
NODE
echo "=== 结算单里的 dest_address 全串核对 ==="
node - "$DIR/coinsettle_CS_demo_user_a_MWC529KI.json" <<'NODE'
const fs=require('fs');const o=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
console.log('  id: '+o.id);
console.log('  ref: '+o.ref+'  asset: '+o.asset+'  amount: '+o.amount);
console.log('  source: '+o.source);
console.log('  dest: '+o.dest+'  chain: '+o.dest_chain);
console.log('  dest_address: '+o.dest_address);
console.log('  匹配 owner coinbase (0xe35b...093c): '+(o.dest_address&&o.dest_address.toLowerCase()==='0xe35b920ba38bc83fb19d0b77871545c2f986093c'));
console.log('  status: '+o.status);
NODE
echo "done"
