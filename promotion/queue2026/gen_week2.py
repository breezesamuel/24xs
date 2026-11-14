# -*- coding: utf-8 -*-
"""第二周封面生成 — 7个新角度"""
from PIL import Image, ImageDraw, ImageFont
import os, json

OUT = r"F:/2026/24xs/promotion/queue2026"

def font(size, bold=False):
    for p in [r"C:/Windows/Fonts/msyhbd.ttc" if bold else r"C:/Windows/Fonts/msyh.ttc",
              r"C:/Windows/Fonts/msyh.ttc", r"C:/Windows/Fonts/simhei.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def blend(c1, c2, r):
    return tuple(int(c1[i]*(1-r)+c2[i]*r) for i in range(3))

THEMES = {
    "dream2":  {"bg": (18,32,48),  "bg2": (8,16,28),  "accent": (110,190,220), "gold": (225,235,245), "icon": "蛇",
                "title": "梦到蛇，是吉是凶？", "sub": "解梦词典 · 蛇的37种梦境场景", "tag": "解 梦 · 蛇 篇"},
    "dream3":  {"bg": (30,24,18),  "bg2": (16,12,8),  "accent": (210,160,90),  "gold": (240,225,190), "icon": "水",
                "title": "梦见发大水，什么征兆？", "sub": "解梦词典 · 水的28种梦境场景", "tag": "解 梦 · 水 篇"},
    "tarot2":  {"bg": (42,16,60),  "bg2": (22,8,34),  "accent": (190,120,240), "gold": (240,220,170), "icon": "恋",
                "title": "TA心里还有你吗？", "sub": "三张牌看清关系状态 · 仅供娱乐", "tag": "塔 罗 · 关 系"},
    "almanac2":{"bg": (14,34,44),  "bg2": (6,18,24),  "accent": (90,190,210),  "gold": (230,240,220), "icon": "宅",
                "title": "本周末适合搬家吗？", "sub": "365天每日黄历 · 搬家/签约/开业吉日", "tag": "黄 历 · 周 末"},
    "zodiac2": {"bg": (50,22,26),  "bg2": (26,10,12), "accent": (235,130,120), "gold": (245,225,180), "icon": "财",
                "title": "属蛇人今年的财运方位", "sub": "12生肖 · 事业/财运/人际每日更新", "tag": "生 肖 · 财 运"},
    "guanyin2":{"bg": (20,38,30),  "bg2": (8,20,16),  "accent": (120,200,150), "gold": (235,235,180), "icon": "愿",
                "title": "心事无处说？摇一支签", "sub": "观音灵签100签 · 上上签35支", "tag": "灵 签 · 心 事"},
    "toolkit2":{"bg": (16,24,40),  "bg2": (8,12,22),  "accent": (100,170,250), "gold": (215,230,250), "icon": "坑",
                "title": "支付集成的12个坑，我踩完了", "sub": "40002签名/NaN金额/证书序号全记录", "tag": "开 发 · 避 坑"},
}

def gen(name, t):
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=blend(t["bg"], t["bg2"], y/H))
    d = ImageDraw.Draw(img)
    for cx, cy, rr in [(900,190,240),(140,1180,280),(960,1300,160)]:
        d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr], outline=blend(t["bg"], t["accent"], 0.25), width=2)
        d.ellipse([cx-rr+30,cy-rr+30,cx+rr-30,cy+rr-30], outline=blend(t["bg"], t["accent"], 0.15), width=1)
    ftag = font(44, bold=True)
    tw = d.textlength(t["tag"], font=ftag)
    d.rounded_rectangle([(W-tw)/2-40, 170, (W+tw)/2+40, 270], radius=50, outline=t["gold"], width=3)
    d.text(((W-tw)/2, 192), t["tag"], font=ftag, fill=t["gold"])
    cyc = 470
    d.ellipse([W/2-170, cyc-170, W/2+170, cyc+170], outline=t["accent"], width=4)
    d.ellipse([W/2-150, cyc-150, W/2+150, cyc+150], fill=blend(t["bg2"], t["accent"], 0.18))
    d.text((W/2, cyc-6), t["icon"], font=font(170, bold=True), fill=(245,245,250), anchor="mm")
    ftitle = font(74, bold=True)
    lines, cur = [], ""
    for ch in t["title"]:
        if d.textlength(cur + ch, font=ftitle) > W - 140: lines.append(cur); cur = ch
        else: cur += ch
    lines.append(cur)
    ty = 740
    for ln in lines:
        d.text((W/2, ty), ln, font=ftitle, fill=(246,246,250), anchor="mm"); ty += 98
    d.line([(W/2-120, ty+16), (W/2+120, ty+16)], fill=t["gold"], width=3)
    d.text((W/2, ty+96), t["sub"], font=font(38), fill=t["accent"], anchor="mm")
    cy0 = ty + 220
    card_fill = blend(t["bg2"], (255,255,255), 0.06)
    for k in range(3):
        x0 = 150 + k*270
        d.rounded_rectangle([x0, cy0, x0+240, cy0+300], radius=20, fill=card_fill, outline=blend(t["bg"],t["accent"],0.55), width=2)
        d.rounded_rectangle([x0+70, cy0+36, x0+170, cy0+136], radius=16, fill=blend(t["bg2"],t["accent"],0.35))
        d.text((x0+120, cy0+86), t["icon"], font=font(56, bold=True), fill=(248,248,252), anchor="mm")
        d.text((x0+120, cy0+200), t["tag"].replace(" ","")[:4], font=font(32, bold=True), fill=blend((255,255,255), t["accent"], 0.5), anchor="mm")
        d.text((x0+120, cy0+250), "每日更新", font=font(24), fill=(150,150,165), anchor="mm")
    d.text((W/2, H-80), "神算阁 · tools.highkingflower.com", font=font(30), fill=(150,150,168), anchor="mm")
    p = os.path.join(OUT, f"cover-{name}.png")
    img.save(p, "PNG")
    return p, os.path.getsize(p)

W2 = {
 "dream2":  {"title": "梦到蛇，是吉是凶？", "topics": ["解梦","梦见蛇","民俗"], "douyin_desc": "梦到蛇不用怕：心理学里蛇=能量与转变，传统解梦里蛇主财。不同场景含义不同：被蛇咬=警示，蛇缠身=压力，白蛇=机遇。37种蛇梦场景都整理好了，看主页。文化娱乐内容，仅供参考。", "body": "梦到蛇不用怕，先看场景。\n心理学视角：蛇=能量与转变（荣格）\n传统解梦：蛇主财，梦中蛇多与金钱焦虑/机会相关\n常见 3 种：\n1️⃣ 被蛇咬：某件事在给你预警\n2️⃣ 蛇缠身：压力贴身，该松绑了\n3️⃣ 白蛇/金蛇：机会正在靠近\n37 种蛇梦场景整理成词典了，看主页。\n文化娱乐内容，仅供参考。"},
 "dream3":  {"title": "梦见发大水，什么征兆？", "topics": ["解梦","心理学","梦境"], "douyin_desc": "水=情绪。梦见大水：涨水=情绪积蓄，清水=好事将近，浑水=心事缠身，被冲走=快撑不住该求助了。28种水的梦境场景整理好了，看主页。娱乐+自我梳理，仅供参考。", "body": "水在梦里=情绪。\n荣格：水是潜意识的经典意象\n常见 4 种：\n1️⃣ 涨水：情绪在积蓄，找出口\n2️⃣ 清水：好事将近，心态在线\n3️⃣ 浑水：心事缠身，理不清\n4️⃣ 被水冲走：快撑不住了，该求助\n28 种水的梦境场景整理成词典了，看主页。\n娱乐+自我梳理，仅供参考。"},
 "tarot2":  {"title": "TA心里还有你吗？", "topics": ["塔罗","感情","自我成长"], "douyin_desc": "不预测未来，只帮你把关系现状看清楚：三张牌=你的状态/对方的状态/你们之间的氛围。塔罗是娱乐+自我梳理工具，答案永远在你自己手里。看主页。仅供参考。", "body": "与其猜，不如把现状看清楚。\n三张牌的读法：\n1️⃣ 第一张=你现在的状态\n2️⃣ 第二张=对方的状态\n3️⃣ 第三张=你们之间的氛围\n不预测未来，只给一个自我观照的坐标。答案永远在你自己手里。\n塔罗是娱乐+心理梳理工具，仅供参考。"},
 "almanac2":{"title": "本周末适合搬家吗？", "topics": ["老黄历","搬家","传统文化"], "douyin_desc": "搬家/签约/开业前看一眼：每日宜忌+吉神方位+冲煞，365天全部做好页面。本周末哪天宜搬家？看主页查。传统文化内容，仅供参考。", "body": "搬家/签约/开业前，扫一眼再定。\n每日黄历包含：\n✔ 宜：搬家/签约/开业/谈判（每天更新）\n✘ 忌：冲动消费/仓促决定\n· 吉神方位\n· 冲煞提醒\n365 天的每日黄历页都做好了，收藏天天看（看主页）。\n传统文化内容，仅供参考。"},
 "zodiac2": {"title": "属蛇人今年的财运方位", "topics": ["生肖运势","财运","传统文化"], "douyin_desc": "12生肖每日运势：事业/财运/人际三张牌。属蛇的看过来，其他生肖也都有。运势是参考坐标，现金流才是硬道理。看主页。娱乐内容，仅供参考。", "body": "运势是参考坐标，现金流才是硬道理。\n每日三张牌：\n💼 事业：今天适合推进还是收尾\n💰 财运：消费欲/进账机会提醒\n🤝 人际：谁值得搭把手\n12 个生肖每天更新，收藏天天看（看主页）。\n娱乐内容，仅供参考，不构成任何建议。"},
 "guanyin2":{"title": "心事无处说？摇一支签", "topics": ["观音灵签","解压","传统文化"], "douyin_desc": "100支观音灵签：上签乘势，中签守己，下签待时。抽签不是算命，是给心事一个出口。全部100支做成了页面，每一支都有签文和解读。看主页。文化娱乐内容，仅供参考。", "body": "抽签不是算命，是给心事一个出口。\n100 支签的节奏：\n· 上签 35 支：乘势而上，保持谦逊\n· 中签 45 支：脚踏实地，不骄不躁\n· 下签 20 支：静待时机，修己安人\n每一支都有签文和解读（看主页）。\n文化娱乐内容，仅供参考。"},
 "toolkit2":{"title": "支付集成的12个坑，我踩完了", "topics": ["程序员","独立开发","踩坑"], "douyin_desc": "中国支付集成12个真实坑：40002签名对不上的排查顺序、NaN金额、微信证书序列号、回调验签、幂等查单……全部踩完并修复，打包成源码包。省你2-4周。看主页工具包。", "body": "中国支付集成，我踩过的 12 个坑：\n1️⃣ 40002 签名错误：先查密钥再查参数顺序\n2️⃣ 金额 NaN：配置对象格式 vs 数字格式\n3️⃣ 微信证书序列号三件套\n4️⃣ 回调验签 + 幂等查单\n……每个坑都是真实订单验证过的修复。\n打包成了源码工具包（看主页），省你 2-4 周。"},
}

results = {}
for k, v in W2.items():
    p, sz = gen(k, THEMES[k])
    results[k] = {"cover": f"cover-{k}.png", "title": v["title"], "body": v["body"], "topics": v["topics"], "douyin_desc": v["douyin_desc"], "status": "queued-week2"}
    print(k, sz)

# merge into posts.json
pj = os.path.join(OUT, "posts.json")
q = json.load(open(pj, encoding="utf-8"))
for k, v in results.items():
    q["queue"].append({"day": len(q["queue"])+1, **v})
q["week2_added"] = "2026-11-02"
json.dump(q, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("queue total:", len(q["queue"]))
