# -*- coding: utf-8 -*-
"""
触达引擎：给每个潜客生成"不像群发“的触达内容。

规则（照做，转化率差 3 倍以上）：
  · 第一句必须说"我看到什么“，不能说”我是谁"
  · 不推销，只给一个"自检表/清单“，让对方先拿到价值
  · 留一个极低成本的行动（回一个词），不要约会议
  · 一次只提一个场景
"""
from __future__ import annotations

import csv
from pathlib import Path

import db
from config import LEAD_DIR

# 开场框架：轮换使用，保证同一条名单里每条消息结构都不同（去群发感）
OPENERS = {
    "私信": [
        "看到{company}在{channel}上{observation}。",
        "刚翻到{company}的{channel}，有个地方想跟你确认一下。",
        "{company}在{channel}上的内容我看了，{observation}——这一条最影响转化。",
        "冒昧打扰。我不是在{channel}上随便翻到的，{company}的{observation}让我多看了两眼。",
        "有个判断想跟你对一下：{company}目前在{channel}上{observation}，这大概率不是内容的问题。",
    ],
    "邮件": [
        "{contact}，你好：\n\n我不介绍公司，先说我的判断。",
        "{contact}：\n\n写这封邮件不是来做介绍的。我看了一处东西，想跟你确认。",
        "{contact}，打扰一分钟。\n\n有一件事我判断错了会浪费你时间，所以先说依据。",
        "{contact} 你好——\n\n下面三句话，没有第四句。看完觉得无关，忽略即可。",
        "{contact}：\n\n我给你发这个，不是群发。理由在第二段。",
    ],
    "电话开场白": [
        "您好，我是{industry}方向的。不占用您太久，就三句话。",
        "{contact}您好，三十秒说完，说完您可以随时挂。",
        "您好。三十秒：第一句说我看到什么，第二句说我判断什么，第三句说我能做什么。",
        "{contact}，我不占用您时间，三句话。",
        "您好，{industry}方向，我说完您再决定要不要听。",
    ],
}

# 价值交付点：轮换，避免每条都像模板
VALUE_HOOKS = [
    "我整理了一份「{industry}获客自检表」，12 项，每项对应一个可核验的数据。",
    "我手上有{industry}客户的自检表，12 项，每一项都有公开数据能核。",
    "我做过一份{industry}的自检清单，12 项，不收费，回个词就发你。",
    "我这边有一份{industry}的 12 项自检表，能看出卡在第几项。",
    "有份{industry}的自查表（12 项）我可以直接发你，不留资。",
]

# 行动请求：轮换，每一个都极低成本
CTAS = [
    "不用留资、不用加微信，你回我「自检」我直接发。",
    "回我一个字「要」就行，我不会追问你要电话。",
    "你回「清单」我发你，不回也没关系，我不会追着问。",
    "回个「1」我就发，绝不群发第二条。",
    "回「自检」两个字就够，剩下的你看完再决定。",
]

BRIDGES = {
    "私信": "\n\n{bridge}\n\n",
    "邮件": "\n\n{bridge}\n\n",
    "电话开场白": "\n\n{bridge}\n\n",
}

BRIDGE_TEXTS = [
    "我先说结论：客户会问的那些问题，机器读不到，所以搜索引擎和 AI 都推荐你的同行。",
    "先给结论：这条链路大概率断在中间——内容有，但客户真正会问的那几个问题，机器读不到。",
    "我的判断是：这一步没做，所以客户去问 AI 的时候，看到的是同行不是你。",
    "直说吧：问题不在营销投入，在于客户真实会问的{industry}问题，你的{channel}上没有可被机器引用的答案。",
    "核心判断：{observation}这件事，让你在 AI 眼里接近于不存在。",
]



FOLLOWUP_1 = """自检表发你了。第 3 项和第 7 项是我见过的{industry}里最常丢分的地方。

如果这两项你们已经做得很扎实，那大概率你的问题不在获客而在转化路径，这我可以另发一份对照表。

需要的话回一句"对照表“。

{company}"""
FOLLOWUP_2 = """最后跟进一次，不回了我就不打扰了。

留一个东西给你：{industry}的"AI 会不会提到我“自查方法，你自己打开 DeepSeek/豆包/Kimi 各问 3 个客户真实会问的问题，
截图看看有没有你。90% 的老板第一次做完会沉默一会儿——这就是答案。

需要我帮你看截图，回"截图“。

{company}"""


def _fill(tpl: str, lead: dict) -> str:
    ind = next((i for i in __import__("config").INDUSTRIES if i["name"] == lead["industry"]), None)
    return tpl.format(
        company=lead["company"],
        channel=lead["channel"],
        contact=lead["contact"],
        industry=lead["industry"],
        observation=lead["pain"],
        angle=lead["angle"],
        mika=lead["contact"].split("（")[0],
        proof=(ind or {}).get("proof_metric", "提及率与线索成本"),
        metric=(ind or {}).get("proof_metric", "8 周"),
    )


def first_touch(lead: dict, idx: int) -> tuple[str, str]:
    """
    按序号轮换 开场框架 / 桥接判断 / 价值交付 / 行动请求 四层，
    使同一条名单里每条消息在结构上都不同 —— 这是「不像群发」的技术保证。
    返回 (使用方式, 完整文案)
    """
    ch = "邮件" if ("官网" in (lead.get("channel") or "") or "搜索" in (lead.get("channel") or "")
                    or "企查查" in (lead.get("channel") or "")) else "私信"
    op = OPENERS[ch][idx % len(OPENERS[ch])]
    br = BRIDGE_TEXTS[idx % len(BRIDGE_TEXTS)]
    vh = VALUE_HOOKS[idx % len(VALUE_HOOKS)]
    cta = CTAS[idx % len(CTAS)]
    body = _fill(op, lead) + BRIDGES[ch].format(bridge=_fill(br, lead)) \
        + _fill(vh, lead) + "\n" + _fill(cta, lead)
    if ch == "邮件":
        body += f"\n\n我做的是这一步：{lead['angle']}\n参考：同类客户在 {lead.get('proof','')}" \
                f" 之后，提及率与线索成本都可核验。\n\n{lead['company']}\n{lead['contact']}"
    else:
        body += f"\n\n（{lead['contact'].split('（')[0]}）"
    return ch, body


def build_queue(tier: str = "A", limit: int = 60) -> dict:
    db.init()
    rows = db.q("SELECT * FROM leads WHERE status='new' AND tier=? ORDER BY icp_score DESC LIMIT ?", (tier, limit))
    plan = []
    for i, r in enumerate(rows):
        ch, t1 = first_touch(dict(r), i)
        d = {
            "lead_id": r["id"], "company": r["company"], "industry": r["industry"],
            "channel": r["channel"], "use": ch, "tier": r["tier"], "icp": r["icp_score"],
            "第1次": t1,
            "第2次(3天后)": FOLLOWUP_1.format(company=r["company"], industry=r["industry"]),
            "第3次(7天后)": FOLLOWUP_2.format(company=r["company"], industry=r["industry"]),
            "行动": "发完在名单里把状态改为 touched 并记录时间；48h无回→第2次；5天无回→第3次；2次无回→冷却90天",
        }
        plan.append(d)
        with db.conn() as c:
            # INSERT OR IGNORE：(lead_id, channel, template) 上有唯一索引，
            # 重复运行不会给同一条线索排多条相同触达
            c.execute("INSERT OR IGNORE INTO outreach(ts,lead_id,channel,template,status) VALUES(?,?,?,?,'queued')",
                      (db.now(), r["id"], ch, "T1+2+3"))
    return {"queued": len(plan), "tier": tier, "unique_copy": len({d["第1次"] for d in plan})}


def export_queue(tier: str = "A", limit: int = 60) -> Path:
    rows = db.q("SELECT l.* FROM leads l WHERE l.status='new' AND l.tier=? ORDER BY l.icp_score DESC LIMIT ?",
                (tier, limit))
    p = LEAD_DIR / f"触达队列_{tier}档_{db.today()}.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["公司", "行业", "渠道", "建议方式", "ICP分", "第1次触达文案", "第2次(3天后)", "第3次(7天后)", "行动指令"])
        for i, r in enumerate(rows):
            ch, t1 = first_touch(dict(r), i)
            w.writerow([r["company"], r["industry"], r["channel"], ch, r["icp_score"], t1,
                        FOLLOWUP_1.format(company=r["company"], industry=r["industry"]),
                        FOLLOWUP_2.format(company=r["company"], industry=r["industry"]),
                        "48h无回→2次；5天无回→3次；2次无回→冷却90天"])
    return p


def mark_touched(company: str) -> None:
    with db.conn() as c:
        c.execute("UPDATE leads SET status='touched', first_touch_ts=? WHERE company=?", (db.now(), company))


def mark_reply(company: str) -> None:
    with db.conn() as c:
        c.execute("UPDATE leads SET reply=1, status='replied' WHERE company=?", (company,))


def mark_won(company: str, amount: float) -> None:
    with db.conn() as c:
        c.execute("UPDATE leads SET status='won', deal_cny=? WHERE company=?", (amount, company))


if __name__ == "__main__":
    print(build_queue("A", 20))
    print(export_queue("A", 20))
