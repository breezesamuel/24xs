#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const PLAN = path.join(H, 'hidden_plan.json');

function main(){
  const tasks=[
    {id:'HP1', name:'鎰熺煡锛圙itHub+缃戦〉锛?, pri:10},
    {id:'HP2', name:'绛涢€夆啋鑷姩鍏ュ簱锛堟矙绠憋級', pri:10},
    {id:'HP3', name:'鍏ㄨ嚜鍔ㄥ瀹?, pri:10},
    {id:'HP4', name:'鍏ㄨ嚜鍔ㄥ鍛?, pri:10},
    {id:'HP5', name:'鍏ㄨ嚜鍔–RM鎺ㄨ繘', pri:10},
    {id:'HP6', name:'鍏ㄨ嚜鍔∣MS灞ョ害+鍞悗', pri:10},
    {id:'HP7', name:'鑷涔犺嚜杩涘寲', pri:9}
  ].sort((a,b)=>b.pri-a.pri);
  const plan={ ts:new Date().toISOString(), mode:'full_autonomous_hidden', focus:tasks[0].name, tasks };
  fs.writeFileSync(PLAN, JSON.stringify(plan,null,2));
  episodic('hidden_planner',{focus:plan.focus});
  console.log('[hidden_planner] ok');
}
main();
