# -*- coding: utf-8 -*-
"""官网部署到 Vercel（生产域名，PC 关机后依然可访问）。

与 watchdog 的 cloudflared 隧道分工：
  - Vercel  = 对外正式地址，托管在 Vercel CDN，永久可访问，不依赖本机
  - 隧道    = 仅本机调试用，域名每次重启都会变

幂等：只有 index.html 内容真正变化时才重新部署。
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent / "10_官网"
INDEX = SITE_DIR / "index.html"
STAMP = Path(__file__).resolve().parent / "watchdog" / "site_deploy.json"
PROJECT = "geo-audit-24xs"
# 部署指纹必须覆盖全部对外文件。早先只算 index.html，
# 导致 subscribe.html 或 api/*.py 改动会被误判成"没变化"而跳过部署 ——
# 改完代码线上却没变，极难排查。
DEPLOY_FILES = [SITE_DIR / n for n in (
    "index.html", "subscribe.html",
    # AI 可抓取入口：漏掉这三个，自己的站就通不过自家体检
    "robots.txt", "llms.txt", "sitemap.xml",
)]


def sync_paylib() -> int:
    """把定价表和支付网关复制进部署目录。

    这两个模块在 01_引擎 / 08_军团 下，Vercel 只发布 10_官网，拿不到。
    复制而不是重写，是为了保持"改价只改一处"——verify 第 19 项就是靠这个。
    目标目录用 _ 前缀：Vercel 不会把 _ 开头的文件当路由，但会打进包里。
    """
    dst = SITE_DIR / "api" / "_paylib"
    dst.mkdir(parents=True, exist_ok=True)
    srcs = {
        SITE_DIR.parent / "01_引擎" / "subscription.py": dst / "subscription.py",
        SITE_DIR.parent / "08_军团" / "capital" / "payment_gateway.py":
            dst / "payment_gateway.py",
    }
    n = 0
    for s, d in srcs.items():
        if not s.exists():
            print(f"[WARN] 源文件缺失: {s}")
            continue
        d.write_bytes(s.read_bytes())
        n += 1
    return n


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def site_digest() -> str:
    """把要发布的文件按路径排序后合并哈希，顺序固定以便复现。"""
    files = [f for f in DEPLOY_FILES if f.exists()]
    files += sorted((SITE_DIR / "api").rglob("*.py"))
    h = hashlib.sha256()
    for f in sorted(set(files)):
        h.update(f.relative_to(SITE_DIR).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def find_vercel() -> list[str]:
    """返回可直接 subprocess 执行的 vercel 命令。

    Windows 上 npm 全局包只装出 vercel.ps1/.cmd shim，subprocess 找不到裸名，
    必须用绝对路径的 .cmd，并配合 shell=True（.cmd 不是原生 exe）。
    """
    import os
    import shutil

    # node + js 入口最稳，不依赖 shim
    shim = shutil.which("vercel.cmd") or shutil.which("vercel")
    if shim:
        return [shim]
    appdata = os.environ.get("APPDATA", "")
    p = Path(appdata) / "npm" / "vercel.cmd"
    if p.exists():
        return [str(p)]
    raise FileNotFoundError("找不到 vercel CLI，请先 npm install -g vercel")


def vercel(*args: str) -> tuple[int, str]:
    cmd = find_vercel() + list(args)
    r = subprocess.run(cmd, cwd=str(SITE_DIR),
                       capture_output=True, text=True, errors="replace",
                       shell=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def current_url() -> str | None:
    if not STAMP.exists():
        return None
    try:
        return json.loads(STAMP.read_text(encoding="utf-8")).get("production_url")
    except Exception:
        return None


def deploy(force: bool = False) -> str | None:
    if not INDEX.exists():
        print(f"[FAIL] 站点文件不存在: {INDEX}")
        return None

    sync_paylib()
    digest = site_digest()
    prev = {}
    if STAMP.exists():
        try:
            prev = json.loads(STAMP.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    if not force and prev.get("sha256") == digest and prev.get("production_url"):
        print(f"[SKIP] 站点内容未变化，沿用 {prev['production_url']}")
        return prev["production_url"]

    code, out = vercel("deploy", "--prod", "--yes", "--name", PROJECT)
    # Vercel 构建失败时 CLI 仍可能返回 0，若只看返回码会把"旧站还活着"
    # 误判成"新版本上线成功"。必须显式检查输出里的错误。
    low = out.lower()
    failed = code != 0 or "error:" in low or "could not parse" in low
    if failed:
        print(f"[FAIL] vercel 部署失败 rc={code}")
        print(out[-800:])
        return None

    url = None
    for line in out.splitlines():
        if "Aliased" in line and "https://" in line:
            url = line.split("https://", 1)[1].strip().strip('"').strip("'")
    if url and not url.startswith("http"):
        url = f"https://{url}"
    if not url:
        url = f"https://{PROJECT}.vercel.app"

    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(json.dumps(
        {"sha256": digest, "production_url": url}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[OK] 已部署: {url}")
    return url


def _wininet_proxy() -> str | None:
    """读 WinINET 系统代理。

    这台机器开了本地代理 127.0.0.1:7897（ProxyEnable=1）。
    urllib 和 curl 都不读 WinINET 设置，只有 Invoke-WebRequest 读，
    所以直连会 timeout——不是站点挂了，是没走代理。
    """
    if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        return None
    if sys.platform != "win32":
        return None
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        enable, _ = winreg.QueryValueEx(k, "ProxyEnable")
        if not enable:
            return None
        server, _ = winreg.QueryValueEx(k, "ProxyServer")
        server = str(server)
        if "=" in server:  # 形如 http=127.0.0.1:7897;https=...
            for part in server.split(";"):
                if part.startswith("https="):
                    server = part.split("=", 1)[1]
                    break
        return server
    except Exception:
        return None


def _opener():
    import urllib.request
    proxy = _wininet_proxy()
    if proxy:
        if "://" not in proxy:
            proxy = f"http://{proxy}"
        return urllib.request.build_opener(urllib.request.ProxyHandler({
            "http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def verify(url: str | None = None) -> bool:
    import time
    import urllib.request

    url = url or current_url() or f"https://{PROJECT}.vercel.app"
    if not url.startswith("http"):
        url = f"https://{url}"

    body, code = None, None
    # Vercel 部署后 CDN 需几秒生效，重试几次
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _opener().open(req, timeout=30) as r:
                code, body = r.status, r.read().decode("utf-8", "replace")
            break
        except Exception as e:
            if attempt == 3:
                print(f"[FAIL] 线上访问失败 {url}: {e}")
                return False
            time.sleep(5)

    ok = code == 200 and "GEO" in (body or "")
    print(f"[{'PASS' if ok else 'FAIL'}] 线上 {url} -> HTTP {code}, {len(body or ''):,} 字符")
    if not ok:
        return False
    for bad in ("非模拟", "数据全部来自实测"):
        if bad in body:
            print(f"[FAIL] 线上页面仍含违规承诺词: {bad}")
            return False
    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    u = deploy(force=force)
    raise SystemExit(0 if verify(u) else 1)
