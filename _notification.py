# Notification service with multiple providers, templates, retry logic
import json, smtplib, secrets, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

# Email templates
TEMPLATES = {
    "purchase_confirmation": {
        "subject": "【丙大山数字资产】购买确认 - {asset_name}",
        "html": """<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 24px;">
<div style="background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%); border-radius: 12px; padding: 32px; color: #e5e7eb;">
<h1 style="color: #22c55e; margin: 0 0 8px;">购买确认</h1>
<p style="color: #9ca3af; margin: 0;">订单号：<strong>{purchase_id}</strong></p>
</div>
<div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-top: 24px;">
<h2 style="margin: 0 0 16px; color: #1f2937;">资产详情</h2>
<table style="width: 100%; border-collapse: collapse;">
<tr><td style="padding: 8px 0; color: #6b7280;">资产名称</td><td style="padding: 8px 0; text-align: right; font-weight: 600;">{asset_name}</td></tr>
<tr><td style="padding: 8px 0; color: #6b7280;">资产类型</td><td style="padding: 8px 0; text-align: right;">{asset_type}</td></tr>
<tr><td style="padding: 8px 0; color: #6b7280;">交付形式</td><td style="padding: 8px 0; text-align: right;">{deliverable}</td></tr>
<tr><td style="padding: 8px 0; color: #6b7280;">许可类型</td><td style="padding: 8px 0; text-align: right;">{license_type}</td></tr>
<tr><td style="padding: 8px 0; color: #6b7280;">金额</td><td style="padding: 8px 0; text-align: right; color: #22c55e; font-weight: 700; font-size: 1.1rem;">¥{amount_cny:.2f}</td></tr>
</table>
</div>
<div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-top: 24px;">
<p style="margin: 0; color: #92400e;"><strong>⚡ 下一步：</strong> 支付完成后，您将收到单独邮件包含一次性下载链接（有效期 24 小时）。请及时下载并妥善保管。</p>
</div>
<div style="text-align: center; margin-top: 24px; color: #9ca3af; font-size: 0.85rem;">
<p>丙大山数字资产平台 · <a href="https://geo-audit-24xs.vercel.app" style="color: #22c55e;">geo-audit-24xs.vercel.app</a></p>
<p>如有疑问，请回复此邮件或联系 supi24@163.com</p>
</div>
</body></html>""",
        "text": "购买确认 - {asset_name}\n订单号: {purchase_id}\n资产类型: {asset_type}\n交付形式: {deliverable}\n许可类型: {license_type}\n金额: ¥{amount_cny:.2f}\n\n支付完成后将发送下载链接（24小时有效）。\n\n丙大山数字资产平台 - geo-audit-24xs.vercel.app"
    },
    "delivery_ready": {
        "subject": "【丙大山数字资产】资产交付 - {asset_name} 下载链接",
        "html": """<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 24px;">
<div style="background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%); border-radius: 12px; padding: 32px; color: #e5e7eb;">
<h1 style="color: #22c55e; margin: 0 0 8px;">资产已就绪，可下载</h1>
<p style="color: #9ca3af; margin: 0;">订单号：{purchase_id}</p>
</div>
<div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-top: 24px;">
<h2 style="margin: 0 0 16px;">{asset_name}</h2>
<p style="color: #6b7280; margin: 0 0 16px;">类型：{asset_type} | 许可：{license_type}</p>
<div style="text-align: center; margin: 24px 0;">
<a href="{download_url}" style="display: inline-block; background: #22c55e; color: #0a0f1a; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 1.05rem;">下载资产 (有效期 24 小时)</a>
</div>
<p style="color: #ef4444; font-size: 0.85rem; margin: 16px 0 0;">⚠️ 链接 24 小时后失效，请立即下载并妥善保管。每个链接仅允许下载 3 次。</p>
</div>
<div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-top: 24px;">
<h3 style="margin: 0 0 8px; color: #92400e;">验证文件完整性</h3>
<pre style="margin: 0; background: #1f2937; color: #22c55e; padding: 12px; border-radius: 6px; font-size: 0.75rem; overflow-x: auto;">sha256sum {asset_filename}\n# 应得: {asset_proof}</pre>
</div>
<div style="text-align: center; margin-top: 24px; color: #9ca3af; font-size: 0.85rem;">
<p>丙大山数字资产平台 · <a href="https://geo-audit-24xs.vercel.app" style="color: #22c55e;">geo-audit-24xs.vercel.app</a></p>
</div>
</body></html>""",
        "text": "资产交付 - {asset_name}\n订单号: {purchase_id}\n下载链接: {download_url} (有效期 24 小时)\nSHA256 校验: {asset_proof}\n请立即下载并验证。\n\n丙大山数字资产平台"
    },
    "subscription_welcome": {
        "subject": "【丙大山数字资产】欢迎加入 {tier_name} 计划",
        "html": """<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 24px;">
<div style="background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%); border-radius: 12px; padding: 32px; color: #e5e7eb;">
<h1 style="color: #22c55e; margin: 0 0 8px;">欢迎加入 {tier_name}</h1>
<p style="color: #9ca3af; margin: 0;">您的订阅已激活，每月 {included_credits:,} 积分已到账</p>
</div>
<div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-top: 24px;">
<h2 style="margin: 0 0 16px;">权益概览</h2>
<ul style="margin: 0; padding-left: 20px; color: #374151;">
<li>月度积分：{included_credits:,}（1 积分 = ¥1）</li>
<li>超额费率：{overage_rate:.0%} 原价</li>
<li>API 访问：包含</li>
<li>优先支持：{'包含' if priority_support else '不包含'}</li>
</ul>
</div>
<div style="text-align: center; margin-top: 24px;">
<a href="https://geo-audit-24xs.vercel.app/dashboard" style="display: inline-block; background: #22c55e; color: #0a0f1a; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none;">进入控制台</a>
</div>
<div style="text-align: center; margin-top: 24px; color: #9ca3af; font-size: 0.85rem;">
<p>丙大山数字资产平台 · <a href="https://geo-audit-24xs.vercel.app" style="color: #22c55e;">geo-audit-24xs.vercel.app</a></p>
</div>
</body></html>""",
        "text": "欢迎加入 {tier_name}\n月度积分: {included_credits:,}\n超额费率: {overage_rate:.0%}\n进入控制台: https://geo-audit-24xs.vercel.app/dashboard"
    },
    "credit_low": {
        "subject": "【丙大山数字资产】积分余额预警 - 仅剩 {remaining_credits:,} 积分",
        "html": """<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 24px;">
<div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 32px; text-align: center;">
<h1 style="color: #92400e; margin: 0 0 8px;">⚠️ 积分余额不足</h1>
<p style="color: #78350f; margin: 0;">当前剩余：<strong style="font-size: 1.5rem;">{remaining_credits:,}</strong> 积分</p>
</div>
<div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-top: 24px; text-align: center;">
<p style="margin: 0 0 16px;">建议：</p>
<ul style="text-align: left; color: #374151; max-width: 300px; margin: 0 auto;">
<li>升级订阅版本获取更多月度积分</li>
<li>购买额外积分包（超额费率 {overage_rate:.0%}）</li>
<li>暂停非必要 API 调用以节省积分</li>
</ul>
</div>
<div style="text-align: center; margin-top: 24px;">
<a href="https://geo-audit-24xs.vercel.app/billing" style="display: inline-block; background: #f59e0b; color: #0a0f1a; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none;">管理账单</a>
</div>
</body></html>""",
        "text": "积分余额预警 - 剩余 {remaining_credits:,} 积分\n建议升级订阅或购买额外积分包。\n管理账单: https://geo-audit-24xs.vercel.app/billing"
    },
    "api_key_created": {
        "subject": "【丙大山数字资产】新 API 密钥已生成",
        "html": """<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 24px;">
<div style="background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%); border-radius: 12px; padding: 32px; color: #e5e7eb;">
<h1 style="color: #22c55e; margin: 0 0 8px;">API 密钥已生成</h1>
<p style="color: #9ca3af; margin: 0;">密钥 ID：{key_id}</p>
</div>
<div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-top: 24px;">
<p style="margin: 0 0 16px;"><strong>您的 API Key（仅显示一次，请立即保存）：</strong></p>
<div style="background: #1f2937; color: #22c55e; padding: 16px; border-radius: 8px; font-family: monospace; word-break: break-all; font-size: 0.85rem;">{api_key}</div>
<p style="color: #ef4444; font-size: 0.85rem; margin: 16px 0 0;">⚠️ 此密钥不会再次显示。如丢失，请撤销并重新生成。</p>
</div>
<div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-top: 24px;">
<h3 style="margin: 0 0 8px; color: #92400e;">安全提示</h3>
<ul style="margin: 0; padding-left: 20px; color: #374151; font-size: 0.9rem;">
<li>请勿将密钥提交至公开代码仓库</li>
<li>建议设置 IP 白名单和速率限制</li>
<li>定期轮换密钥（建议 90 天）</li>
</ul>
</div>
</body></html>""",
        "text": "API 密钥已生成\n密钥 ID: {key_id}\nAPI Key: {api_key}\n\n⚠️ 仅显示一次，请立即保存。"
    }
}

class NotificationService:
    def __init__(self, config: Dict):
        self.config = config
        self.provider = config.get("provider", "smtp")  # smtp, sendgrid, ses, mock
        self.from_email = config.get("from_email", "noreply@geo-audit-24xs.vercel.app")
        self.from_name = config.get("from_name", "丙大山数字资产平台")
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user", "")
        self.smtp_pass = config.get("smtp_pass", "")
        self.sendgrid_key = config.get("sendgrid_api_key", "")
        self.ses_region = config.get("ses_region", "ap-shanghai")
        
    def render(self, template_name: str, **kwargs) -> Dict[str, str]:
        t = TEMPLATES.get(template_name)
        if not t:
            raise ValueError(f"Template not found: {template_name}")
        return {
            "subject": t["subject"].format(**kwargs),
            "html": t["html"].format(**kwargs),
            "text": t["text"].format(**kwargs)
        }
    
    def send(self, to_email: str, template_name: str, **kwargs) -> Dict:
        rendered = self.render(template_name, **kwargs)
        
        if self.provider == "mock":
            # Log to file for development
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "to": to_email,
                "template": template_name,
                "subject": rendered["subject"],
                "provider": "mock"
            }
            log_file = OUT / "notification_log.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            return {"ok": True, "provider": "mock", "message_id": f"mock-{secrets.token_hex(8)}"}
        
        elif self.provider == "smtp":
            return self._send_smtp(to_email, rendered)
        
        elif self.provider == "sendgrid":
            return self._send_sendgrid(to_email, rendered)
        
        elif self.provider == "ses":
            return self._send_ses(to_email, rendered)
        
        return {"ok": False, "error": "unknown_provider"}
    
    def _send_smtp(self, to_email: str, rendered: Dict) -> Dict:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = rendered["subject"]
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg.attach(MIMEText(rendered["text"], "plain", "utf-8"))
            msg.attach(MIMEText(rendered["html"], "html", "utf-8"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user:
                    server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            return {"ok": True, "provider": "smtp"}
        except Exception as e:
            return {"ok": False, "error": str(e), "provider": "smtp"}
    
    def _send_sendgrid(self, to_email: str, rendered: Dict) -> Dict:
        # Requires sendgrid package: pip install sendgrid
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_key)
            mail = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=rendered["subject"],
                plain_text_content=Content("text/plain", rendered["text"]),
                html_content=Content("text/html", rendered["html"])
            )
            resp = sg.send(mail)
            return {"ok": resp.status_code < 400, "provider": "sendgrid", "status_code": resp.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e), "provider": "sendgrid"}
    
    def _send_ses(self, to_email: str, rendered: Dict) -> Dict:
        # Requires boto3: pip install boto3
        try:
            import boto3
            from botocore.exceptions import ClientError
            ses = boto3.client("ses", region_name=self.ses_region)
            resp = ses.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": rendered["subject"], "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": rendered["text"], "Charset": "UTF-8"},
                        "Html": {"Data": rendered["html"], "Charset": "UTF-8"}
                    }
                }
            )
            return {"ok": True, "provider": "ses", "message_id": resp["MessageId"]}
        except Exception as e:
            return {"ok": False, "error": str(e), "provider": "ses"}

# Default config (to be overridden by environment)
DEFAULT_CONFIG = {
    "provider": "mock",
    "from_email": "noreply@geo-audit-24xs.vercel.app",
    "from_name": "丙大山数字资产平台",
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_pass": "",
    "sendgrid_api_key": "",
    "ses_region": "ap-shanghai"
}

# Save config template
config_path = OUT / "notification_config.json"
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

# Save templates reference
with open(OUT / "notification_templates.json", "w", encoding="utf-8") as f:
    json.dump({k: {"subject": v["subject"]} for k, v in TEMPLATES.items()}, f, ensure_ascii=False, indent=2)

# Example usage
if __name__ == "__main__":
    svc = NotificationService(DEFAULT_CONFIG)
    result = svc.send("test@example.com", "purchase_confirmation",
        purchase_id="PUR-20261006-A1B2C3",
        asset_name="采购方画像_上海市医疗器械采购中心",
        asset_type="采购方画像",
        deliverable="结构化JSON档案",
        license_type="commercial-multi-v1",
        amount_cny=500.00
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

print("Notification service module ready")
