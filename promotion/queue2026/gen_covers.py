# -*- coding: utf-8 -*-
"""生成7天发帖队列封面图 1080x1440 (3:4) v2 — 汉字图标+深色卡片"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"F:/2026/24xs/promotion/queue2026"

def font(size, bold=False):
    for p in [r"C:/Windows/Fonts/msyhbd.ttc" if bold else r"C:/Windows/Fonts/msyh.ttc",
              r"C:/Windows/Fonts/msyh.ttc", r"C:/Windows/Fonts/simhei.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

THEMES = {
    "dream":   {"bg": (26,22,64),  "bg2": (10,8,34),  "accent": (155,140,255), "gold": (240,220,150), "icon": "梦",
                "title": "梦到被追，到底在跑什么？", "sub": "一本能查的解梦词典 · 4000+梦境条目", "tag": "解 梦 词 典"},
    "almanac": {"bg": (10,40,30),  "bg2": (5,25,18),  "accent": (80,200,140),  "gold": (245,225,140), "icon": "历",
                "title": "今天适合做什么？", "sub": "每日老黄历 · 宜忌/吉神方位/冲煞", "tag": "每 日 黄 历"},
    "peidui":  {"bg": (70,20,45),  "bg2": (40,8,28),  "accent": (255,130,160), "gold": (245,215,150), "icon": "缘",
                "title": "你和TA配不配？", "sub": "132组生肖配对 · 78组星座配对", "tag": "生 肖 配 对"},
    "poem":    {"bg": (15,35,55),  "bg2": (8,20,35),  "accent": (120,180,230), "gold": (235,220,170), "icon": "诗",
                "title": "今天这首诗，替你说心情", "sub": "每日一签 · 古诗词里的自我观照", "tag": "诗 词 日 签"},
    "guanyin": {"bg": (45,30,15),  "bg2": (25,15,8),  "accent": (220,170,90),  "gold": (245,225,150), "icon": "签",
                "title": "摇一签，安一安心", "sub": "观音灵签100签 · 文化娱乐体验", "tag": "观 音 灵 签"},
    "toolkit": {"bg": (14,20,32),  "bg2": (8,12,20),  "accent": (88,166,255),  "gold": (210,225,245), "icon": "码",
                "title": "17000页工具站，代码全给你", "sub": "支付/SEO/适老化/BYOK · 生产级源码包", "tag": "开 发 者 工 具 包"},
    "zodiac":  {"bg": (55,25,70),  "bg2": (30,12,42), "accent": (200,140,240), "gold": (245,225,155), "icon": "肖",
                "title": "今天你的生肖运势如何", "sub": "事业/财运/人际 · 每日更新", "tag": "生 肖 运 势"},
}

def blend(c1, c2, r):
    return tuple(int(c1[i]*(1-r)+c2[i]*r) for i in range(3))

def gen(name, t):
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    for y in range(H):
        r = y / H
        d.line([(0, y), (W, y)], fill=blend(t["bg"], t["bg2"], r))
    # decorative circles (manual blend onto bg)
    for cx, cy, rr, alpha in [(880,180,260,0.10),(150,1150,300,0.09),(950,1280,180,0.12)]:
        for yy in range(max(0,cy-rr), min(H,cy+rr)):
            half = int((rr*rr - (yy-cy)*(yy-cy)) ** 0.5)
            c = blend(d.textlength and img.getpixel((min(W-1,max(0,cx)), yy)), t["accent"], alpha) if False else None
        # simpler: draw ellipse outline rings instead of fills
    d = ImageDraw.Draw(img)
    # rings (outline style, no alpha issues)
    for cx, cy, rr in [(900,190,240),(140,1180,280),(960,1300,160)]:
        d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr], outline=blend(t["bg"], t["accent"], 0.25), width=2)
        d.ellipse([cx-rr+30,cy-rr+30,cx+rr-30,cy+rr-30], outline=blend(t["bg"], t["accent"], 0.15), width=1)
    # top tag pill
    ftag = font(44, bold=True)
    tw = d.textlength(t["tag"], font=ftag)
    d.rounded_rectangle([(W-tw)/2-40, 170, (W+tw)/2+40, 270], radius=50, outline=t["gold"], width=3)
    d.text(((W-tw)/2, 192), t["tag"], font=ftag, fill=t["gold"])
    # big icon char in circle
    cyc = 470
    d.ellipse([W/2-170, cyc-170, W/2+170, cyc+170], outline=t["accent"], width=4)
    d.ellipse([W/2-150, cyc-150, W/2+150, cyc+150], fill=blend(t["bg2"], t["accent"], 0.18))
    d.text((W/2, cyc-6), t["icon"], font=font(170, bold=True), fill=(245,245,250), anchor="mm")
    # title
    ftitle = font(74, bold=True)
    lines, cur = [], ""
    for ch in t["title"]:
        if d.textlength(cur + ch, font=ftitle) > W - 140:
            lines.append(cur); cur = ch
        else:
            cur += ch
    lines.append(cur)
    ty = 740
    for ln in lines:
        d.text((W/2, ty), ln, font=ftitle, fill=(246,246,250), anchor="mm")
        ty += 98
    d.line([(W/2-120, ty+16), (W/2+120, ty+16)], fill=t["gold"], width=3)
    d.text((W/2, ty+96), t["sub"], font=font(38), fill=t["accent"], anchor="mm")
    # 3 mini cards (dark fill, accent border)
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
    print(name, os.path.getsize(p))

for k, v in THEMES.items():
    gen(k, v)
print("ALL DONE")
