# 引擎说明（零依赖 Python，可直接运行）

> 目标：把"卖 AI 服务"从靠人脑，变成靠代码。
> 依赖：**无**。不需要 `pip install`，不需要 API Key，不需要网络。

---

## 快速开始

```powershell
cd F:\2026\24xs\01_引擎
python cli.py all          # 跑一次全流程
python cli.py dashboard    # 只看今天的看板
```

---

## 七个模块，各自对应一个能卖钱的东西

| 文件 | 对应的商业能力 | 产出 |
|---|---|---|
| `config.py` | 行业库 / 报价库 / 成本口径 / 目标 | 5 个垂直行业的完整交付画像 |
| `db.py` | 复利存量 | SQLite，所有数据可回溯 |
| `geo_audit.py` | **GEO 可见度审计**（引流品 8,000-30,000 元/份） | 探测表 + 诊断报告 + 动作清单 |
| `corpus_gen.py` | **内容工厂**（交付核心资产） | 每行业 7 个可直接发布的文件 |
| `lead_engine.py` | **潜客流水线** | ICP 评分 + 三档名单 CSV |
| `outreach.py` | **个性化触达** | 每人 3 次跟进文案，零群发感 |
| `finance.py` | **现金流与目标追踪** | 回款登记、交付成本、报价下限、跑道成本 |
| `funnel_sim.py` | **1000 万可行性测算** | 四种收入结构 + 渠道 ROI 模拟 |
| `report.py` | **每日决策看板** | 钱 / 漏斗 / 资产 / 今日 4 件事 |

---

## 命令一览

```
python cli.py init                     初始化数据库与目录
python cli.py corpus --all             生成 5 个行业的内容资产
python cli.py corpus home_improvement  只生成家装/装修

python cli.py geo audit  <客户> <行业>   跑 GEO 可见度审计并出报告
python cli.py geo sheet <客户> <行业>   导出人工探测表（填完用 ingest 回填）
python cli.py geo ingest <csv> <客户> <行业>

python cli.py leads                    生成潜客池
python cli.py leads import <csv>       导入真实名单（5 列：司,行业,城市,联系人,痛点）
python cli.py leads list A             导出 A 档名单

python cli.py outreach A               生成并导出 A 档触达队列

python cli.py money in  <客户> <项目> <金额>
python cli.py money out <项目> <金额>
python cli.py money status

python cli.py sim                      生成 1000 万路径测算
python cli.py dashboard                生成每日看板
python cli.py all                      全流程
```

行业 key：`home_improvement`（家装/装修）、`legal`（律师）、`cross_border`（跨境电商）、
`local_service`（本地生活）、`manufacturing`（制造业）

---

## 两个关键设计

### 1. GEO 探测可以是"离线基线"，但绝不能是"假的"

真实探测需要调用各家 AI 平台（要钱、要人工）。所以引擎分两层：

- `probe_offline()`：用可解释的基线概率跑通全流程与指标公式，标注为 `baseline-sim`
- `export_probe_sheet()` / `ingest_csv()`：导出探测表 → 人工或 LLM 逐行回填 → 回填真实数据
  → **所有指标和动作自动重算**

**承诺上的含义**：你可以今天就用基线给客户演示流程和报告格式，
但对客户承诺的效果数字，必须来自 `ingest_csv` 的真实数据。

> **绝不用基线数据对客户承诺效果。** 这是这条业务线唯一不能碰的红线。

### 2. 名单是"实体特征"而不是编造的公司名

`lead_engine.PROSPECTS` 生成的是 `{城市}家装工装公司` 这类**可搜索的实体特征**，
不是虚构的公司名。原因：
- 编造的公司名是死名单，第二次就用不了了
- 实体特征可以天天用来生成新的搜索任务
- 避免"虚构企业信息"的合规风险

导入真实名单用 `leads import`，只要 5 列。

---

## 想改什么，改哪里

| 想改 | 改哪个 |
|---|---|
| 换行业 / 加行业 | `config.py` 的 `INDUSTRIES` |
| 改报价 | `config.py` 的 `PRICING` |
| 改人天成本 | `config.py` 的 `COST` |
| 改目标金额 / 周期 | `config.py` 的 `TARGET_CNY` / `HORIZON_DAYS` |
| 改 GEO 问题模板 | `geo_audit.py` 的 `TEMPLATES` |
| 改触达话术 | `outreach.py` 的 `FIRST_TOUCH` / `FOLLOWUP_1` / `FOLLOWUP_2` |
| 改内容风格 | `corpus_gen.py` 的 `HOOKS` / `geo_corpus()` |
| 改渠道倍数 | `funnel_sim.py` 的 `CHANNELS` |
| 改每日动作 | `report.py` 的 `_today_tasks()` |

**所有数字都是参数，不是硬编码的判断。** 这是这个引擎能被反复调优的前提。

---

## 改完怎么验证

```powershell
python -m py_compile config.py db.py corpus_gen.py geo_audit.py lead_engine.py outreach.py finance.py funnel_sim.py report.py cli.py
python cli.py all
```

`compile` 无输出 = 语法正确。`all` 跑完 = 功能正常。
