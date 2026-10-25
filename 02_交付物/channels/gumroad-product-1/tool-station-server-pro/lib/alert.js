// POST /api/alert —— 告警中继（由本机进程托管时发送，绕开 GitHub 机房 IP 被 QQ 拒绝的问题）
//
// 背景: 24xs 的 AutoOps 告警直接用 QQ SMTP(465)。GitHub Actions 跑在机房 IP 上，
//       QQ 会对这些 IP 返回 535 登录失败 → 告警通道降级为 kv_fallback（人看不到）。
// 方案: Actions → 本机公网入口(隧道) /api/alert → 本机 QQ SMTP → 你的邮箱。
//       本机是家宽 IP，QQ SMTP 实测可用。
import { createRequire } from "node:module";
import net from "node:net";
import tls from "node:tls";

const require = createRequire(import.meta.url);

function env(k) { return process.env[k] || ""; }

function b64(s) { return Buffer.from(String(s), "utf8").toString("base64"); }

/** 裸 TLS 465 + AUTH LOGIN 发信（与 24xs 的实现一致，避免依赖 nodemailer） */
function sendMail({ host, port, user, pass, to, subject, body }) {
  return new Promise((resolve) => {
    if (!user || !pass) return resolve({ ok: false, reason: "smtp_unconfigured" });
    let st = 0, buf = "", done = false, sock = null;
    const line = (s) => { try { sock.write(s + "\r\n"); } catch (e) { /* ignore */ } };
    const finish = (ok, info) => {
      if (done) return; done = true;
      try { sock && sock.end(); } catch (e) { /* ignore */ }
      resolve({ ok, info: info || "" });
    };
    try {
      sock = tls.connect({ host, port: Number(port) || 465, servername: host }, () => {
        sock.on("data", (d) => {
          buf += d.toString("latin1");
          let i;
          while ((i = buf.indexOf("\r\n")) >= 0) {
            const raw = buf.slice(0, i); buf = buf.slice(i + 2);
            const code = parseInt(raw, 10);
            if (code === 220 && st === 0) { line("EHLO relay"); st = 1; }
            else if (code === 250 && st === 1) { line("AUTH LOGIN"); st = 2; }
            else if (code === 334 && st === 2) { line(b64(user)); st = 3; }
            else if (code === 334 && st === 3) { line(b64(pass)); st = 4; }
            else if (code === 235 && st === 4) { line(`MAIL FROM:<${user}>`); st = 5; }
            else if (code === 250 && st === 5) { line(`RCPT TO:<${to}>`); st = 6; }
            else if (code === 250 && st === 6) { line("DATA"); st = 7; }
            else if (code === 354 && st === 7) {
              line(`Subject: ${subject}\r\nFrom: ${user}\r\nTo: ${to}\r\n`
                + `Content-Type: text/plain; charset=UTF-8\r\n\r\n${body}\r\n.`);
              st = 8;
            } else if (code === 250 && st === 8) { line("QUIT"); finish(true); }
            else if (code >= 500) { finish(false, "smtp_" + code); }
            if (done) buf = "";
          }
        });
      });
      sock.on("error", (e) => finish(false, String((e && e.message) || e)));
      sock.setTimeout(15000, () => finish(false, "timeout"));
    } catch (e) {
      finish(false, String((e && e.message) || e));
    }
  });
}

export default async function handler(req, res) {
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ status: "error", message: "Method not allowed" });

  const body = req.body || {};
  const token = env("ALERT_WEBHOOK_TOKEN");
  const given = (req.headers && (req.headers["x-alert-token"] || req.headers["x-webhook-token"])) || "";
  if (token && given !== token) {
    return res.status(403).json({ status: "error", message: "bad token" });
  }

  const subject = String(body.subject || body.topic || "[Alert]").slice(0, 180);
  const text = String(body.message || body.text || JSON.stringify(body)).slice(0, 4000);
  const host = env("SMTP_HOST") || "smtp.qq.com";
  const port = env("SMTP_PORT") || "465";
  const user = env("SMTP_USER");
  const pass = env("SMTP_AUTH");
  const to = env("SMTP_TO") || user;

  const r = await sendMail({ host, port, user, pass, to, subject, text });
  return res.status(r.ok ? 200 : 502).json({
    status: r.ok ? "ok" : "error",
    channel: r.ok ? "smtp" : "failed",
    reason: r.info || undefined,
    to,
  });
}
