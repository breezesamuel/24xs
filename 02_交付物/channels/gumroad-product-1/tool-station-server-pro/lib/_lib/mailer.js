// 收款闭环邮件：SMTP 裸 TLS 465 AUTH LOGIN（与 alert.js 同源，提取到 _lib 复用）
// 环境变量: SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_AUTH / SMTP_TO
// 用法: await sendReceipt({ to, orderId, plan, amountUsd, amountCny, payerEmail, env })

import net from "node:net";
import tls from "node:tls";

function env(k) { return process.env[k] || ""; }
function b64(s) { return Buffer.from(String(s), "utf8").toString("base64"); }

function sendMail({ host, port, user, pass, to, subject, body }) {
  return new Promise((resolve) => {
    if (!user || !pass) return resolve({ ok: false, reason: "smtp_unconfigured" });
    let st = 0, buf = "", done = false, sock = null;
    const line = (s) => { try { sock.write(s + "\r\n"); } catch { /* ignore */ } };
    const finish = (ok, info) => {
      if (done) return; done = true;
      try { sock && sock.end(); } catch { /* ignore */ }
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
      sock.setTimeout(12000, () => finish(false, "timeout"));
    } catch (e) {
      finish(false, String((e && e.message) || e));
    }
  });
}

export async function sendReceipt({ to, orderId, plan, planName, amountUsd, amountCny, payerEmail, env: payEnv }) {
  const host = env("SMTP_HOST") || "smtp.qq.com";
  const port = env("SMTP_PORT") || "465";
  const user = env("SMTP_USER");
  const pass = env("SMTP_AUTH");
  const toAddr = to || env("SMTP_TO") || user;

  const body = [
    `===== 付款回执 =====`,
    `订单号: ${orderId}`,
    `计划:   ${planName || plan}`,
    `金额:   $${amountUsd} (约 ¥${amountCny})`,
    `PayPal 账户: ${payerEmail || "(未提供)"}`,
    `环境:   ${payEnv || "live"}`,
    ``,
    `订阅已激活。`,
    ``,
    `— 系统自动发送`,
  ].join("\n");

  return sendMail({
    host, port, user, pass,
    to: toAddr,
    subject: `【收款确认】订单 ${orderId} · ${planName || plan} · $${amountUsd}`,
    body,
  });
}
