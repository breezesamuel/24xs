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
    {id:'HP1', name:'感知（GitHub+网页）', pri:10},
    {id:'HP2', name:'筛选→自动入库（沙箱）', pri:10},
    {id:'HP3', name:'全自动寻客', pri:10},
    {id:'HP4', name:'全自动外呼', pri:10},
    {id:'HP5', name:'全自动CRM推进', pri:10},
    {id:'HP6', name:'全自动OMS履约+售后', pri:10},
    {id:'HP7', name:'自学习自进化', pri:9}
  ].sort((a,b)=>b.pri-a.pri);
  const plan={ ts:new Date().toISOString(), mode:'full_autonomous_hidden', focus:tasks[0].name, tasks };
  fs.writeFileSync(PLAN, JSON.stringify(plan,null,2));
  episodic('hidden_planner',{focus:plan.focus});
  console.log('[hidden_planner] ok');
}
main();
