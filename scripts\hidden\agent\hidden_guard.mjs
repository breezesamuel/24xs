#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const G = path.join(H, 'hidden_guard.json');

const def={
  mode:'full_autonomous_hidden',
  enforce_robots:true,
  domain_allow:['github.com','raw.githubusercontent.com','gist.github.com','github.io'],
  min_delay_ms:1800,
  forbid_direct_write_verified:true,
  human_gates_disabled:true,
  auto_publish:true,
  auto_outreach:true,
  auto_crm_oms:true
};

function main(){
  if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
  fs.writeFileSync(G, JSON.stringify(def,null,2));
  episodic('hidden_guard_check',{mode:def.mode});
  console.log('[hidden_guard] hidden');
}
main();
