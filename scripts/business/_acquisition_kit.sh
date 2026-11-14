#!/usr/bin/env bash
# 生成"获客分享包": 各渠道(微信/小红书/GitHub/知乎)发帖文案 + 渠道码 + 短链
python3 - <<'PY'
import json
B_CN='https://tools-cn.highkingflower.com/get.html'
B_VER='https://tools.highkingflower.com/get.html'
# 渠道码 (让留资归属到渠道, 统计哪条链接带量)
chan={'wechat':'wx','xiaohongshu':'xhs','github':'gh','zhihu':'zh','bilibili':'bili'}
out=[]
out.append('# 获客分享包 · 让 /get.html 有流量进 (喂"新trial→留邮箱→自动升级"线)')
out.append('')
out.append('> 用法: 复制对应渠道文案发出去, 把 [链接] 换成该渠道码的落地页。每个渠道码让留资可归属, 便于统计哪条带来新 trial 用户。')
out.append('>')
out.append('> 落地页: 国内 %s · 海外 %s'%(B_CN,B_VER))
out.append('')
# 各渠道文案 (合规: 不夸大收益, 含"非投资建议")
posts={
 '微信(个人/朋友圈)':'【免费量化回测】把你的交易策略跑一遍真实回测: 年化/最大回撤/Sharpe/胜率, 一键出专业报告, 免费 7 天体验全部工具。留个邮箱, 到期自动提醒升级(9折)。历史回测不代表未来, 非投资建议。[链接]',
 '小红书(笔记)':'量化党/交易党看过来📊 把策略丢进去就能跑真实回测, 年化/回撤/胜率/Sharpe 全有, 免费试 7 天, 还能导出专业 PDF 报告。不是荐股, 纯工具, 历史回测不代表未来哦~ 链接放评论区👇  #量化交易 #策略回测 #工具分享',
 'GitHub(仓库README/issue)':'[Tool] Quant strategy backtester with real market data (public K-lines) — annualized return / max drawdown / Sharpe / win rate, export professional PDF report. Free 7-day trial, auto upgrade nudge to your email. Not investment advice; historical backtest ≠ future returns. [link]',
 '知乎(回答/文章)':'做一个量化策略回测工具应该看哪些指标? (年化收益/最大回撤/Sharpe/胜率) 我最近在用丙大山的回测工具, 把策略喂进去跑真实公开 K 线, 直接出专业报告, 免费 7 天体验。注意: 回测是历史数据, 不代表未来, 非投资建议。[链接]',
 'B站(简介/弹幕区)':'做策略不会回测? 这个工具把你策略喂进去跑真实行情, 年化/回撤/Sharpe/胜率 全给你算好, 还能导出 PDF 报告, 免费试 7 天。历史回测不代表未来, 非投资建议, 风险自负。[链接]',
}
for ch,text in posts.items():
    code=chan.get(ch,ch.lower().split('(')[0])
    link=f'{B_CN}?ref={code}'
    out.append(f'## {ch}')
    out.append(f'- 渠道码: {code}')
    out.append(f'- 落地页: {link}')
    out.append(f'- 文案:')
    out.append(f'  > {text}')
    out.append('')
out.append('## 渠道码对照 (统计带量)')
out.append('| 渠道 | 码 | 落地页 |')
out.append('|---|---|---|')
for ch,code in chan.items():
    out.append(f'| {ch} | {code} | {B_CN}?ref={code} |')
out.append('')
out.append('## 为什么这样能赚钱 (闭环)')
out.append('流量点链接 → 落地页留邮箱(/api/contact 持久化) → 免费7天 → 到期 bd-trial-winback 自动读留资发升级邮件 → 客户点邮件链接付款 → 支付宝自动到账 + 自动开通订阅')
out.append('即: 每带来 1 个留邮箱的新 trial 用户, 到期就有 1 次自动升级收款机会(¥60~500)。')
out.append('')
out.append('> 诚实: 文案不夸大收益, 均含"非投资建议/历史回测不代表未来"合规声明。分享出去才会真带流量, 页面只是入口。')
open('/opt/bingdashan/data/billing/acquisition_kit.md','w').write('\n'.join(out))
print('已写 /opt/bingdashan/data/billing/acquisition_kit.md (%d 渠道)'%len(posts))
PY
echo "=== 预览获客包 (前 25 行) ==="
head -25 /opt/bingdashan/data/billing/acquisition_kit.md
echo done
