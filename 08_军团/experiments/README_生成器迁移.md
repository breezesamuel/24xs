已删除的生成器（2026-09-30）
==========================

gen_pet_eml.py / gen_dental_eml.py / gen_outreach_eml.py / gen_kidscode_eml.py

删除原因：这四个脚本各带一份硬编码公司名单 + 硬编码报告文件名，
与磁盘上的真实文件名各走各的。实测后果：

  - 24 封草稿里 18 封正文写"见附件"但**根本没有附件**
  - 有附件的 6 封附的是 .md，正文却说"我把 PDF 发您"
  - 21 封正文写"整改报价（6–15 万）"，低于硬下限 221,000
  - 24 封都写"加微信 460123249（同 QQ）"，而 CONTACT_WECHAT 从未配置
  - 报告名 18/21 指向不存在的文件

替代方案：gen_all_drafts.py（唯一入口）
  名单 = 99_产出/获客名单/真实名单_*.csv
  报告 = 99_产出/报告/真实客户审计/*.md（按公司名模糊匹配）
  附件 = 报告转 HTML，浏览器可打开、可打印 PDF
  闸门 = 收件人 / 报告可解析 / 附件非空 / 报价不破底线 / 不冒充微信 / 垂类不串味

体检：python -X utf8 08_军团/experiments/audit_drafts.py
回归：python -X utf8 08_军团/experiments/test_audit_drafts.py