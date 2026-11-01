import sys,smtplib,ssl
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
ctx=ssl.create_default_context()
msg=MIMEText("Hiring team at Mitre Media,\n\nRe: the Tech Lead Full-Stack Rails Engineer opening (posted on RemoteOK).\n\nApplying on behalf of BingDashaN Intelligent Technology (Shanghai) — an AI-track software\ncompany available for remote contract or contract-to-hire engagements.\n\nPublicly verifiable production work:\n1. 11,000+ page production site (5,775 tools + 5,305 HTML5 games, 5 languages with RTL,\n   three-rail checkout verified with real orders): https://tools.highkingflower.com\n2. Deterministic agents API (537 automated tests, JSON in/out):\n   https://bingdashanai.highkingflower.com/agents\n3. Open-source generator core (MIT): https://github.com/breezesamuel/micro-tool-factory\n\nStrongest fit: TypeScript/Node full-stack at content-scale, payment integrations to\nproduction standard (idempotent order queries, webhook verification, fail-closed config),\nand shipping fast without framework lock-in.\n\nReply to this email and we can walk through the live codebase on a screen share.\n\nBingDashaN Intelligent Technology (Shanghai)\n",'plain','utf-8')
msg['Subject']=Header("Application: Tech Lead Full-Stack Rails Engineer — BingDashaN (live portfolio)",'utf-8')
msg['From']=formataddr(("上海丙大山智能科技","460123249@qq.com"))
msg['To']="jobs@mitremedia.com"
with smtplib.SMTP_SSL("smtp.qq.com",465,context=ctx,timeout=40) as s:
    s.login("460123249@qq.com","vcibttgugksebhgc")
    s.sendmail("460123249@qq.com",["jobs@mitremedia.com"],msg.as_string())
print('SENT')