# -*- coding: utf-8 -*-
"""验收自测：以 GM 视角检查这个系统能不能留下、能不能自己跑。

1-7  基础引擎（旧版）
8    官网存在且不含"非模拟"等虚假数据声明
9    7x24 看护程序 + 启动计划任务
10   资金安全：密钥不入库、报税 fail-closed、无硬编码身份
11   Node/npm 可解析（Windows 裸 npm 会 [WinError 2]）
12   情报 MCP 输出为真实抓取而非离线样本
13   `cli.py all` 重跑不累积数据（重复公司/重复触达/唯一索引）
19   订阅页展示价格与后台结算价一致（防止改价不同步）
20   收款合规：条款/退款/隐私齐全，且公开页不含任何凭据
"""
import csv
import io
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from config import OUT_DIR, REPORT_DIR  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
ok = 0
total = 22

print("=" * 68)
print("  验收自测  ——  以 GM 视角检查这个系统能不能留下并自己跑")
print("=" * 68)

# 1
try:
    p = REPORT_DIR / "最新看板.md"
    t = p.read_text(encoding="utf-8")
    checks = ["已进账", "距目标缺口", "日均需进账", "潜客池", "今日动作"]
    miss = [c for c in checks if c not in t]
    r = (not miss) and len(t) > 800
    print(f"[{'PASS' if r else 'FAIL'}] 1 看板有真实数字            {p.name} ({len(t)} 字)" + (f" 缺:{miss}" if miss else ""))
    ok += r
except Exception as e:
    print(f"[FAIL] 1 看板 {e}")

# 2  真实名单质量：条数、报告配套、占位符清零、隔离状态
#    旧版这里检查"模拟触达队列≥30条"，但那份队列是合成数据、按设计绝不外发，
#    拿它当验收标准等于奖励造假。改为校验真实核验名单。
verified = db.scalar("SELECT COUNT(*) FROM leads WHERE status='new_verified'")
total_leads = db.scalar("SELECT COUNT(*) FROM leads")
needs_contact = db.scalar("SELECT COUNT(*) FROM leads WHERE status='needs_contact'")

vfiles = sorted((OUT_DIR / "获客名单").glob("真实名单_*.csv"))
vrows, placeholder_hits = 0, []
for f in vfiles:
    with f.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            vrows += 1
            blob = " ".join(str(x) for x in row.values())
            for bad in ("REPLACE_ME", "REPLACE_ME_PHONE", "REPLACE_ME_EMAIL", "待补", "TODO"):
                if bad in blob:
                    placeholder_hits.append(f"{f.name}:{bad}")
            # 至少有一种可触达方式
            if not any(str(row.get(k, "")).strip() for k in ("电话", "邮箱", "微信")):
                placeholder_hits.append(f"{f.name}:无联系方式")

audit_dir = REPORT_DIR / "真实客户审计"
audit_reports = len(list(audit_dir.glob("GEO审计_*.md"))) if audit_dir.exists() else 0
eml_dir = OUT_DIR / "外发草稿"
eml_count = len(list(eml_dir.glob("外发_*.eml"))) if eml_dir.exists() else 0

r = (verified >= 20 and vrows >= verified and not placeholder_hits
     and audit_reports >= verified and eml_count >= 5)
print(f"[{'PASS' if r else 'FAIL'}] 2 真实名单质量              核验 {verified} 家 / CSV {vrows} 行 / "
      f"报告 {audit_reports} 份 / 草稿 {eml_count} 封 / 待补联系 {needs_contact} 家")
if placeholder_hits:
    print(f"        问题: {placeholder_hits[:5]}")
if vrows < verified:
    print(f"        CSV 行数 {vrows} < 库内 new_verified {verified}，有线索没落盘")
if needs_contact:
    print(f"        注意: {needs_contact} 家因联系方式无效已退回 needs_contact，不计入核验数")
ok += r

# 3
corpus = sorted((OUT_DIR / "内容语料").glob("*/*.md"))
chars = sum(len(p.read_text(encoding="utf-8")) for p in corpus)
r = len(corpus) >= 30 and chars > 40000
print(f"[{'PASS' if r else 'FAIL'}] 3 内容可直接发布            {len(corpus)} 个文件 / {chars:,} 字符")
ok += r

# 4
with db.conn() as c:
    fl = c.execute("SELECT COUNT(*) FROM geo_probes").fetchone()[0]
    co = c.execute("SELECT COUNT(*) FROM corpus").fetchone()[0]
    ld = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    out = c.execute("SELECT COUNT(*) FROM outreach").fetchone()[0]
r = fl > 0 and co > 0 and ld > 0 and out > 0
print(f"[{'PASS' if r else 'FAIL'}] 4 数据库有真实读库数据      探测 {fl} / 语料 {co} / 潜客 {ld} / 触达 {out}")
ok += r

# 5
from finance import delivery_cost, quote_floor  # noqa: E402
cost = delivery_cost(6, 8, 12, 10, 10, 200)
floor = quote_floor(cost)
r = 100000 < floor < 400000
print(f"[{'PASS' if r else 'FAIL'}] 5 报价有硬底线              成本 {cost['total_cost']:,} 元 → 报价下限 {floor:,} 元")
ok += r

# 6
sim = (OUT_DIR / "财务" / "1000万路径测算.md")
t = sim.read_text(encoding="utf-8")
r1 = "A_纯服务" in t
r2 = "❌ 不达标" in t
r3 = "现实折扣" in t
r = r1 and r2 and r3
print(f"[{'PASS' if r else 'FAIL'}] 6 测算是诚实的              纯服务显示不达标={r2}  含折扣={r3}")
ok += r

# 7
tk = sorted((ROOT / "07_运维").glob("*"))
r = len(tk) >= 3 and any("run_daily" in f.name for f in tk)
print(f"[{'PASS' if r else 'FAIL'}] 7 明天知道怎么自动跑        运维脚本 {len(tk)} 个")
ok += r

# 8 官网：存在 + 不含虚假数据声明
try:
    site = ROOT / "10_官网" / "index.html"
    t = site.read_text(encoding="utf-8")
    # 这些词一旦出现就是在对外做无法支撑的实测承诺
    false_claims = ["非模拟", "数据全部来自实测", "全部实测"]
    bad = [c for c in false_claims if c in t]
    # 反向要求：必须披露样例含模拟基线
    disclose = ("baseline-sim" in t) or ("基线模拟" in t) or ("样例" in t)
    r = site.exists() and not bad and disclose and len(t) > 3000
    print(f"[{'PASS' if r else 'FAIL'}] 8 官网文案不虚假承诺        {len(t):,} 字符"
          f"  违规词={bad or '无'}  已披露样例={disclose}")
    ok += r
except Exception as e:
    print(f"[FAIL] 8 官网 {e}")

# 9 看护程序 + 启动任务
try:
    wd = ROOT / "07_运维" / "watchdog.py"
    src = wd.read_text(encoding="utf-8")
    comp_ok = wd.exists() and "ensure" in src and "parse_tunnel_url" in src
    # 计划任务注册情况
    task = ""
    try:
        import subprocess
        r2 = subprocess.run(["schtasks", "/Query", "/TN", "24xs_Watchdog"],
                            capture_output=True, text=True, errors="replace")
        task = "已注册" if r2.returncode == 0 else "未注册"
    except Exception:
        task = "查询失败"
    state = ROOT / "07_运维" / "watchdog" / "state.json"
    live = False
    if state.exists():
        import json
        try:
            live = bool(json.loads(state.read_text(encoding="utf-8")).get("public_url"))
        except Exception:
            pass
    r = comp_ok and task == "已注册"
    print(f"[{'PASS' if r else 'FAIL'}] 9 7x24 看护已就位           启动任务={task}  公网地址={'有' if live else '无'}")
    ok += r
except Exception as e:
    print(f"[FAIL] 9 看护 {e}")

# 10 资金安全回归
try:
    sys.path.insert(0, str(ROOT / "08_军团"))
    import subprocess
    r2 = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q",
                         str(ROOT / "08_军团" / "capital" / "tests")],
                        capture_output=True, text=True, errors="replace",
                        cwd=str(ROOT / "08_军团"))
    out = (r2.stdout or "") + (r2.stderr or "")
    r = r2.returncode == 0
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or ["无输出"]
    print(f"[{'PASS' if r else 'FAIL'}] 10 资金安全门禁有效        {tail[0][:56]}")
    ok += r
except Exception as e:
    print(f"[FAIL] 10 资金安全 {e}")

# 11 Node 可解析
try:
    sys.path.insert(0, str(ROOT / "08_军团"))
    from workers.node_bridge import find_node, find_npm, find_npx, node_version
    node, npm, npx = find_node(), find_npm(), find_npx()
    ver = node_version()
    r = bool(node and npm and npx)
    print(f"[{'PASS' if r else 'FAIL'}] 11 Node 工具链可用          node={os.path.basename(node or '未找到')} 版本={ver or '?'} npm/npx={bool(npm) and bool(npx)}")
    ok += r
except Exception as e:
    print(f"[FAIL] 11 Node 工具链 {e}")

# 12 情报为真实 MCP 抓取
try:
    f = ROOT / "08_军团" / "intel" / "rebuild_opportunities.json"
    if f.exists():
        import json
        d = json.loads(f.read_text(encoding="utf-8"))
        opps = d if isinstance(d, list) else d.get("opportunities", [])
        # 离线样本是固定的 4 条公司；真实 MCP 结果应与之不同且数量更大
        r = len(opps) >= 1 and any("sim" not in str(o.get("source", "")).lower() for o in opps)
        src = (opps[0].get("source") if opps else "?")
        print(f"[{'PASS' if r else 'FAIL'}] 12 情报来自真实 MCP        {len(opps)} 条机会 / source={src}")
    else:
        r = False
        print(f"[FAIL] 12 情报文件缺失 {f}")
    ok += r
except Exception as e:
    print(f"[FAIL] 12 情报 {e}")

# 13 幂等性
try:
    with db.conn() as c:
        dup_lead = c.execute("""SELECT COUNT(*) FROM (
            SELECT company FROM leads WHERE TRIM(COALESCE(company,''))<>''
            GROUP BY company HAVING COUNT(*)>1)""").fetchone()[0]
        dup_out = c.execute("""SELECT COUNT(*) FROM (
            SELECT lead_id,channel,template FROM outreach
            GROUP BY 1,2,3 HAVING COUNT(*)>1)""").fetchone()[0]
        has_idx = c.execute("""SELECT COUNT(*) FROM sqlite_master
            WHERE type='index' AND name IN
            ('idx_leads_company','idx_outreach_lead','idx_probe_dedupe','idx_corpus_dedupe')""").fetchone()[0]
    r = dup_lead == 0 and dup_out == 0 and has_idx == 4
    print(f"[{'PASS' if r else 'FAIL'}] 13 重跑不累积数据            重复公司={dup_lead} 重复触达={dup_out} 唯一索引={has_idx}/4")
    ok += r
except Exception as e:
    print(f"[FAIL] 13 幂等性 {e}")

# 14 生产域名可访问（PC 关机后仍可用）
try:
    sys.path.insert(0, str(ROOT / "07_运维"))
    from deploy_site import current_url, verify as site_verify
    url = current_url()
    r = bool(url) and site_verify(url)
    print(f"[{'PASS' if r else 'FAIL'}] 14 生产域名在线（关机可用）  {url or '未部署'}")
    ok += r
except Exception as e:
    print(f"[FAIL] 14 生产域名 {e}")

# 15 官网有可用转化入口（否则投了广告也接不住）
try:
    t = (ROOT / "10_官网" / "index.html").read_text(encoding="utf-8")
    has_form = "leadForm" in t
    # 必须解析出"非空且非占位"的联系方式，否则等于没有转化入口
    m_email = re.search(r'var\s+CONTACT_EMAIL\s*=\s*"([^"]*)"', t)
    m_wechat = re.search(r'var\s+CONTACT_WECHAT\s*=\s*"([^"]*)"', t)
    email_val = (m_email.group(1).strip() if m_email else "")
    wechat_val = (m_wechat.group(1).strip() if m_wechat else "")

    def usable(v: str) -> bool:
        return bool(v) and "REPLACE_ME" not in v and "待补" not in v and len(v) >= 5

    has_email = bool(re.match(r"^[^@\s]+@[^@\s.]+\.[A-Za-z]{2,}", email_val))
    has_wechat = usable(wechat_val)
    contact_ok = has_email or has_wechat
    # 微信若已填，页面必须真的把它渲染出来
    wechat_rendered = (not has_wechat) or ("wechatId" in t)

    r = has_form and contact_ok and wechat_rendered
    print(f"[{'PASS' if r else 'FAIL'}] 15 官网有可用转化入口        表单={has_form} "
          f"邮箱={email_val or '未配置'}{'(有效)' if has_email else '(无效)'} "
          f"微信={wechat_val or '未配置'}")
    ok += r
except Exception as e:
    print(f"[FAIL] 15 转化入口 {e}")

# 16 已核验名单与自动发送队列必须隔离
try:
    with db.conn() as c:
        nv = c.execute("SELECT COUNT(*) FROM leads WHERE status='new_verified'").fetchone()[0]
        leaked = c.execute("""SELECT COUNT(*) FROM outreach o
                              JOIN leads l ON l.id=o.lead_id
                              WHERE l.status='new_verified'""").fetchone()[0]
    r = leaked == 0
    print(f"[{'PASS' if r else 'FAIL'}] 16 已核验名单未自动外发      已核验={nv} 家 泄漏进队列={leaked}")
    ok += r
except Exception as e:
    print(f"[FAIL] 16 名单隔离 {e}")

# 17 联系方式卫生：库里不允许残留非法号码（网页噪音 / 不存在区号）
# 同时扫真实名单 CSV —— CSV 是源文件，只清库不扫源，哪天重新导入
# 垃圾号就又回来了（之前就发生过一次）。
try:
    import phoneutil
    import re as _re
    tok = _re.compile(r"1[3-9]\d{9}|0\d{9,11}|400[-\s]?\d{3,4}[-\s]?\d{3,4}")
    offenders = []
    with db.conn() as c:
        for row in c.execute("SELECT id, company, contact, channel FROM leads "
                             "WHERE contact IS NOT NULL OR channel<>''"):
            blob = f"{row['contact'] or ''} {row['channel'] or ''}"
            for t in tok.findall(blob):
                if not phoneutil.is_valid(t):
                    offenders.append(f"DB:{row['id']}:{row['company']}:{t}")

    lead_dir = ROOT / "99_产出" / "获客名单"
    csv_files = [p for p in sorted(lead_dir.glob("真实名单_*.csv"))
                 if ".bak-" not in p.name]
    for p in csv_files:
        with p.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                blob = " ".join(str(row.get(k) or "") for k in ("电话", "微信"))
                for t in tok.findall(blob):
                    if not phoneutil.is_valid(t):
                        offenders.append(f"CSV:{p.name}:{row.get('公司')}:{t}")

    # 备份文件不能和真名单混在同一目录，否则按 glob 读会把备份当名单读一遍
    stray = [p.name for p in lead_dir.glob("真实名单_*.csv") if ".bak-" in p.name]

    r = not offenders and not stray
    print(f"[{'PASS' if r else 'FAIL'}] 17 联系方式格式卫生          "
          f"非法号码 {len(offenders)} 条（库 + {len(csv_files)} 个名单文件）")
    if stray:
        print(f"        名单目录混入了备份文件 {stray}（会被当成名单重复读取）")
    if offenders:
        print(f"        {offenders[:6]}")
    ok += r
except Exception as e:
    print(f"[FAIL] 17 联系方式卫生 {e}")

# 18 外发草稿合规：冒充微信 / 报价低于硬底线 / 垂类串味 / 空附件
# 这一项挡的是"发出去才发现"的错。之前 24 封草稿同时中了两枪：
# 正文承诺"加微信 460123249"（微信从未配置）和"整改报价 6–15 万"
# （低于硬下限 221,000），还有 18 封写着"见附件"却根本没附件。
try:
    import subprocess as _sp
    _env = dict(os.environ, PYTHONIOENCODING="utf-8")
    _p = _sp.run([sys.executable, "-X", "utf8",
                  r"F:\2026\24xs\08_军团\experiments\audit_drafts.py"],
                 capture_output=True, text=True, encoding="utf-8", env=_env)
    _out = _p.stdout or ""
    m = _re.search(r"结论：\s*(\d+)\s*处问题", _out)
    nbad = int(m.group(1)) if m else -1
    r = (_p.returncode == 0 and nbad == 0)
    print(f"[{'PASS' if r else 'FAIL'}] 18 外发草稿合规（微信/报价/垂类/附件）  问题 {nbad} 处")
    if not r:
        for line in _out.splitlines():
            if "[FAIL]" in line:
                print(f"        {line.strip()}")
    ok += r
except Exception as e:
    print(f"[FAIL] 18 草稿合规 {e}")

# 19 订阅页与后台定价一致（防止页面改了价、后台还按旧价结算）
try:
    import subscription as _sub
    sp = ROOT / "10_官网" / "subscribe.html"
    page = sp.read_text(encoding="utf-8") if sp.exists() else ""
    miss = []
    for lg in ("cn", "en"):
        for period, it in _sub.PLANS[lg]["plans"].items():
            # 价格要能在页面上原样找到（60 / 9.9 这种写法）
            txt = f"{it['price']:g}"
            if txt not in page:
                miss.append(f"{lg}/{period}={txt}")
    if f"{_sub.FREE_USES}" not in page:
        miss.append(f"免费次数 {_sub.FREE_USES} 未出现在页面")
    r = bool(page) and not miss
    print(f"[{'PASS' if r else 'FAIL'}] 19 订阅页价格与配置一致      "
          f"{'全部一致' if r else '对不上: ' + ','.join(miss)}")
    ok += r
except Exception as e:
    print(f"[FAIL] 19 订阅定价一致性 {e}")

# 20 收款合规：条款齐全 + 站点绝不泄露凭据
# 这一项是防止把密钥/账户写进公开页面。index.html 和 subscribe.html
# 都会被 Vercel 部署成公开可读，写进去等于全网可见。
try:
    site_files = [ROOT / "10_官网" / "index.html",
                  ROOT / "10_官网" / "subscribe.html"]
    txt = "\n".join(f.read_text(encoding="utf-8") for f in site_files
                    if f.exists())
    # 订阅页必须有服务条款、退款政策、隐私政策
    need_terms = {"服务条款": "服务条款", "退款政策": "退款",
                  "隐私政策": "隐私"}
    lack = [k for k, v in need_terms.items() if v not in txt]

    # 任何形式的凭据都不得出现在公开页面
    leaks = []
    for pat, label in (
        (r"[A-Za-z0-9+/]{80,}={0,2}", "疑似密钥/长 Base64"),
        (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
         "UUID 型凭据"),
        (r"\b\d{16,19}\b", "疑似银行账号"),
        (r"(?i)(secret|api[_-]?key|token)\s*[:=]\s*\S{12,}", "硬编码凭据"),
        (r"\bEA[A-Z0-9]{20,}\b", "PayPal 凭据"),
        (r"(?i)alipay\.com|ICBC|BANK_CODE", "支付网关凭据"),
    ):
        for m in re.finditer(pat, txt):
            leaks.append(f"{label}: {m.group()[:24]}...")

    r = not lack and not leaks
    print(f"[{'PASS' if r else 'FAIL'}] 20 收款合规（条款+无凭据泄露）  "
          f"缺条款={lack or '无'}  泄露={len(leaks)}")
    for x in (lack and [f"缺 {x}"] or []) + leaks[:4]:
        print(f"        {x}")
    ok += r
except Exception as e:
    print(f"[FAIL] 20 收款合规 {e}")

# 21 支付宝支付链路完好（安全回归 + 线上真下单）
try:
    import subprocess
    # a) 端点安全用例：伪造回调、金额不符、无凭据必须全部拒绝
    r3 = subprocess.run([sys.executable, "-X", "utf8",
                         str(ROOT / "08_军团" / "experiments" / "test_alipay_api.py")],
                        capture_output=True, text=True, errors="replace",
                        cwd=str(ROOT / "08_军团" / "experiments"))
    o3 = (r3.stdout or "") + (r3.stderr or "")
    tail3 = [l for l in o3.strip().splitlines() if l.strip()][-1:] or ["无输出"]
    safe = r3.returncode == 0
    print(f"[{'PASS' if safe else 'FAIL'}] 21 支付链路安全用例      {tail3[0][:56]}")
    if not safe:
        for l in o3.splitlines():
            if "[FAIL]" in l:
                print(f"        {l.strip()[:90]}")
    ok += safe
except Exception as e:
    print(f"[FAIL] 21 支付链路安全 {e}")

# 22 支付代码里没有硬编码私钥，且回调端点确实做了主动查询
try:
    apidir = ROOT / "10_官网" / "api"
    pay = (apidir / "alipay_pay.py").read_text(encoding="utf-8")
    notify = (apidir / "alipay_notify.py").read_text(encoding="utf-8")
    lib = (apidir / "alipay_lib.py").read_text(encoding="utf-8")
    src = pay + notify + lib
    body_bad = []
    for pat, label in ((r"MII[A-Za-z0-9+/]{200,}", "疑似私钥"),
                       (r"(?i)app_id\s*=\s*['\"]\d{12,}", "硬编码 APP_ID")):
        for m in re.finditer(pat, src):
            body_bad.append(label)
    # 凭据只能来自环境变量
    env_ok = "ALIPAY_PRIVATE_KEY" in lib and "os.environ" in lib
    # 回调必须主动查支付宝；网关必须比对金额
    q = "query_trade" in notify
    amt = "expected_amount" in (
        ROOT / "08_军团" / "capital" / "payment_gateway.py").read_text(encoding="utf-8")
    r = not body_bad and env_ok and q and amt
    print(f"[{'PASS' if r else 'FAIL'}] 22 支付代码无硬编码凭据  "
          f"硬编码={body_bad or '无'} env读取={env_ok} 回调主动查询={q} 金额校验={amt}")
    ok += r
except Exception as e:
    print(f"[FAIL] 22 支付凭据卫生 {e}")

print("-" * 68)
print(f"  结果：{ok}/{total} 项通过")
print("=" * 68)
sys.exit(0 if ok == total else 1)
