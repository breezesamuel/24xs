# APILayer 上架材料 — Deterministic Agents API

**基址**: https://bingdashanai.highkingflower.com/agents （OpenAPI: /agents/openapi.json，70 路径）

**提交流程**: apilayer.com → Submit API → 用 openapi.json 导入 → 定价按 RapidAPI 同档折算（Free 25/mo · Basic $5/300 · Pro $15/1500 · Ultra $49/6000）。

**Listing 摘要（EN，直接粘贴）**:
```
Five deterministic business agents — code, data, finance, process, sales.
Same input, same output, every time. JSON in/out, synchronous /run and
async /tasks with monthly quotas and /usage metering. 537 automated tests.
No hallucinations: finance math, reconciliation and approval chains you can
embed in production workflows.
```

**鉴权**：买家自助开通已建好——`POST /rapidapi/provision`（传 rapid_key+email 返回 token）。
APILayer 若支持自定义头转发则同 RapidAPI 方案 B；不支持则先用方案 A（手动发 token）。

**自检**：`GET /agents/health` 免费 200（含 5 agent 实时状态），上架审核直接看这里。
