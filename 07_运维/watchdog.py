# -*- coding: utf-8 -*-
"""
watchdog.py — 7×24 常驻看护进程

职责：
  1. 托管官网静态服务器（http.server）
  2. 托管 cloudflared 隧道，暴露公网 URL
  3. 周期性跑每日流水线（引擎 + 安全回归 + 情报）
  4. 任何子进程崩溃自动拉起；自身崩溃由计划任务拉起

设计约束：
  - 只做无资金影响的本地/公开可逆动作
  - 不触碰支付、报税、分红、外发邮件
  - 所有动作写日志，磁盘保留 30 天
"""
import json
import os
import subprocess
import sys
import time
import signal
import socket
import shutil
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"F:\2026\24xs")
SITE_DIR = ROOT / "10_官网"
LOG_DIR = ROOT / "07_运维" / "watchdog"
STATE_FILE = LOG_DIR / "state.json"
PIPELINE_INTERVAL_SEC = int(os.environ.get("WD_PIPELINE_INTERVAL", 6 * 3600))
SERVER_PORT = int(os.environ.get("WD_SERVER_PORT", 8788))
TUNNEL_ENABLED = os.environ.get("WD_TUNNEL", "1") == "1"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    # 追加写，失败不致命
    try:
        with open(LOG_DIR / f"watchdog_{datetime.now():%Y%m}.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def prune_logs(days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    for f in LOG_DIR.glob("watchdog_*.log"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            try:
                f.unlink()
            except Exception:
                pass


@dataclass
class Child:
    name: str
    argv: list
    cwd: Path
    env: dict = field(default_factory=lambda: os.environ.copy())
    proc: object = None
    restarts: int = 0
    last_start: float = 0.0
    # 崩溃后多久允许重启，防止疯狂重启打满 CPU
    backoff_sec: float = 3.0
    # 需要抓取 stdout 时（如隧道 URL），在此指定文件；必须在 Popen 时传入，
    # 事后再赋值 proc.stdout 不生效（管道已按 DEVNULL 建立）
    out_file: object = None

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        stdout = self.out_file if self.out_file is not None else subprocess.DEVNULL
        self.proc = subprocess.Popen(
            self.argv, cwd=str(self.cwd), env=self.env,
            stdout=stdout,
            stderr=subprocess.STDOUT if self.out_file is not None else subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.last_start = time.time()
        log(f"[start] {self.name} pid={self.proc.pid} argv={' '.join(self.argv[:3])}")

    def ensure(self):
        if self.alive():
            return
        if self.last_start and (time.time() - self.last_start) < self.backoff_sec:
            return
        self.restarts += 1
        # 退避随重启次数增长，上限 60s
        self.backoff_sec = min(60.0, 3.0 * self.restarts)
        self.start()
        log(f"[restart] {self.name} 第 {self.restarts} 次")


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def http_ok(url: str, timeout: float = 8.0) -> tuple[bool, int]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "watchdog/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status == 200 and b"GEO" in body, r.status
    except Exception as e:
        log(f"[http] {url} 失败: {e}")
        return False, 0


def find_cloudflared() -> str | None:
    """定位真实的 cloudflared.exe

    注意：npm 包 'cloudflared' 只是一个 node 包装脚本（cloudflared.js），
    没有真正的可执行文件，且用 subprocess 启动 .cmd 会丢失 stdout，
    导致抓不到 trycloudflare 公网地址。必须用 exe。
    """
    exe = shutil.which("cloudflared.exe") or shutil.which("cloudflared")
    if exe and exe.lower().endswith(".exe"):
        return exe
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "cloudflared" / "cloudflared.exe"
    if local.exists():
        return str(local)
    if exe:
        # 找到了但不是 exe（.cmd/.ps1 shim），仍可用，只是可能抓不到 stdout
        return exe
    return None


def parse_tunnel_url(logfile: Path, since_offset: int = 0) -> str | None:
    """从 cloudflared 输出里抓 trycloudflare 公网地址

    since_offset: 只扫描该字节偏移之后的内容。快速隧道每次重启 URL 都变，
    若全量扫描会匹配到上一次进程的失效地址（旧 URL 返回 530），
    导致健康检查一直打在一个已死的域名上。
    """
    if not logfile.exists():
        return None
    try:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            if since_offset:
                f.seek(since_offset)
            txt = f.read()
    except Exception:
        return None
    import re
    m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", txt)
    return m.group(0) if m else None



def run_pipeline():
    """跑每日流水线：引擎 + 安全回归 + 情报。全部无资金影响。"""
    log("[pipeline] 开始每日流水线")
    steps = [
        ("engine", ROOT / "01_引擎", [sys.executable, "-X", "utf8", "cli.py", "all"]),
        ("security", ROOT / "08_军团", [sys.executable, "-X", "utf8",
                                        str(ROOT / "08_军团" / "capital" / "tests" / "test_security.py")]),
        ("intel", ROOT / "08_军团", [sys.executable, "-X", "utf8",
                                     str(ROOT / "08_军团" / "intel" / "lootdrop_intel.py")]),
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    results = {}
    for key, cwd, argv in steps:
        try:
            r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                               timeout=1800, env=env, errors="replace")
            ok = r.returncode == 0
            results[key] = ok
            if key == "security" and not ok:
                # 安全测试失败 = 可能有人破坏了 fail-closed，必须显式告警
                log(f"[ALERT] 资金栈安全测试失败！退出码 {r.returncode}")
                log((r.stderr or r.stdout or "")[-1200:])
            else:
                log(f"[pipeline] {key}: {'OK' if ok else 'FAIL rc=' + str(r.returncode)}")
        except subprocess.TimeoutExpired:
            results[key] = False
            log(f"[pipeline] {key}: TIMEOUT")
        except Exception as e:
            results[key] = False
            log(f"[pipeline] {key}: 异常 {e}")
    prune_logs()
    return results


def save_state(d: dict):
    try:
        STATE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class Watchdog:
    def __init__(self):
        self.children: list[Child] = []
        self.stopping = False
        self.tunnel_log = LOG_DIR / "cloudflared.log"
        self.last_pipeline = 0.0
        self.last_health = 0.0
        self.health_fail = 0
        self.state = {"started_at": datetime.now().isoformat(), "public_url": None,
                      "local_port": SERVER_PORT, "pipeline_runs": 0}

    def setup_site_server(self):
        if not (SITE_DIR / "index.html").exists():
            log(f"[fatal] 站点文件不存在: {SITE_DIR / 'index.html'}")
            return False
        argv = [sys.executable, "-X", "utf8", "-m", "http.server", str(SERVER_PORT),
                "--bind", "127.0.0.1", "--directory", str(SITE_DIR)]
        c = Child("site_server", argv, ROOT)
        c.start()
        self.children.append(c)
        # 等端口起来
        for _ in range(20):
            if port_open(SERVER_PORT):
                log(f"[site] 本地站点就绪 http://127.0.0.1:{SERVER_PORT}")
                return True
            time.sleep(0.5)
        log("[site] 端口未就绪")
        return False

    def setup_tunnel(self):
        exe = find_cloudflared()
        if not exe:
            log("[tunnel] 未找到 cloudflared，跳过公网暴露")
            return None
        argv = [exe, "tunnel", "--url", f"http://127.0.0.1:{SERVER_PORT}",
                "--no-autoupdate"]
        env = os.environ.copy()
        # 记录起始偏移：只认本次进程产生的 URL，避免命中上一轮失效地址
        base_offset = self.tunnel_log.stat().st_size if self.tunnel_log.exists() else 0
        # 必须把 stdout/stderr 直接重定向到文件，才能抓到 trycloudflare 地址
        out = open(self.tunnel_log, "a", encoding="utf-8", errors="replace")
        c = Child("cloudflared", argv, ROOT, env)
        c.out_file = out
        c.start()
        self.children.append(c)
        for _ in range(90):
            url = parse_tunnel_url(self.tunnel_log, base_offset)
            if url and url != self.state.get("public_url"):
                ok, code = http_ok(url)
                if ok:
                    log(f"[tunnel] 公网地址就绪 {url} (HTTP {code})")
                    self.state["public_url"] = url
                    return url
            time.sleep(1)
        log("[tunnel] 90s 内未取得可用公网地址")
        return None

    def run_forever(self):
        log("=" * 60)
        log("watchdog 启动（7x24 常驻）")
        log(f"站点目录: {SITE_DIR}")
        log(f"流水线间隔: {PIPELINE_INTERVAL_SEC}s")
        self.setup_site_server()
        if TUNNEL_ENABLED:
            self.setup_tunnel()
        else:
            log("[tunnel] 已通过 WD_TUNNEL=0 禁用")
        save_state(self.state)

        # 启动后先立刻跑一次流水线
        run_pipeline()
        self.state["pipeline_runs"] = 1
        self.last_pipeline = time.time()
        save_state(self.state)

        while not self.stopping:
            for c in self.children:
                c.ensure()

            # 站点健康检查（限频，避免刷屏；连续失败则标记而非反复请求）
            now = time.time()
            if now - self.last_health > 60:
                self.last_health = now
                if not port_open(SERVER_PORT):
                    log("[health] 本地端口不可达，等待 site_server 自动拉起")
                    self.state["local_ok"] = False
                else:
                    self.state["local_ok"] = True

                url = self.state.get("public_url")
                if url:
                    ok, code = http_ok(url)
                    self.state["public_http"] = code if ok else None
                    if ok:
                        self.health_fail = 0
                    else:
                        self.health_fail += 1
                        log(f"[health] 公网站点异常 HTTP={code} (连续 {self.health_fail} 次)")
                        if self.health_fail >= 3:
                            # 隧道多半已断，重置 URL 让重新发现
                            log("[health] 公网连续失败，清空 URL 待隧道重建")
                            self.state["public_url"] = None

            if time.time() - self.last_pipeline > PIPELINE_INTERVAL_SEC:
                run_pipeline()
                self.state["pipeline_runs"] += 1
                self.last_pipeline = time.time()

            self.state["children"] = {c.name: {"pid": c.proc.pid if c.proc else None,
                                               "restarts": c.restarts,
                                               "alive": c.alive()}
                                       for c in self.children}
            self.state["heartbeat"] = datetime.now().isoformat()
            save_state(self.state)
            time.sleep(5)

        log("[stop] 收到停止信号，关闭子进程")
        for c in self.children:
            if c.alive():
                try:
                    c.proc.terminate()
                except Exception:
                    pass
        save_state(self.state)


def main():
    wd = Watchdog()

    def handler(signum, frame):
        log(f"[signal] 收到 {signum}")
        wd.stopping = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, handler)
        except Exception:
            pass

    # 写 pid 文件，便于外部查询
    try:
        (LOG_DIR / "watchdog.pid").write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    wd.run_forever()


if __name__ == "__main__":
    main()
