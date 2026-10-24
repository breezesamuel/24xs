# -*- coding: utf-8 -*-
"""
node_bridge.py — 跨平台定位 Node.js 可执行文件与包管理器

背景：Windows 上 npm/npx 通常同时存在 `npx`（sh 脚本）、`npx.cmd`、`npx.ps1`。
Python 的 subprocess 在 shell=False 时只会解析可执行文件与 PATHEXT 中的
`*.exe`/`.com`，**不会**解析裸 `npx` 或 `npx.ps1`，于是报
`[WinError 2] 系统找不到指定的文件`。本模块统一解决该问题。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Windows 上 node 常见的非 PATH 安装位置
_WINDOWS_CANDIDATES = [
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
    r"C:\ProgramData\nvm",
    r"C:\Users\%s\AppData\Roaming\nvm" % os.environ.get("USERNAME", ""),
    r"C:\Users\%s\AppData\Local\Programs\nodejs" % os.environ.get("USERNAME", ""),
    r"C:\Users\%s\scoop\apps\nodejs\current" % os.environ.get("USERNAME", ""),
    r"C:\Users\%s\scoop\apps\nodejs-lts\current" % os.environ.get("USERNAME", ""),
]

# 在 Windows 上优先使用 .cmd 包装器：它能被 CreateProcess 直接执行，
# 而裸 `npx`（无扩展名的 sh 脚本）与 `npx.ps1` 不能。
_EXE = ".exe" if sys.platform != "win32" else ".cmd"


def _is_windows() -> bool:
    return os.name == "nt"


def find_node() -> Optional[str]:
    """定位 node 可执行文件的绝对路径"""
    exe = shutil.which("node.exe" if _is_windows() else "node")
    if exe:
        return exe
    for d in _WINDOWS_CANDIDATES:
        p = Path(d) / "node.exe"
        if p.exists():
            return str(p)
    return None


def find_npm() -> Optional[str]:
    """定位 npm（Windows 优先 npx.cmd/npm.cmd 这类真正可执行的包装器）"""
    if _is_windows():
        for name in ("npm.cmd", "npm.exe"):
            p = shutil.which(name)
            if p:
                return p
    found = shutil.which("npm")
    if found:
        return found
    for d in _WINDOWS_CANDIDATES:
        p = Path(d) / ("npm.cmd" if _is_windows() else "npm")
        if p.exists():
            return str(p)
    return None


def find_npx() -> Optional[str]:
    """定位 npx（Windows 优先 npx.cmd）"""
    if _is_windows():
        for name in ("npx.cmd", "npx.exe"):
            p = shutil.which(name)
            if p:
                return p
    found = shutil.which("npx")
    if found:
        return found
    for d in _WINDOWS_CANDIDATES:
        p = Path(d) / ("npx.cmd" if _is_windows() else "npx")
        if p.exists():
            return str(p)
    return None


def node_env() -> dict:
    """构造包含 Node 安装目录的 PATH，供 subprocess 使用"""
    env = os.environ.copy()
    node_dir = Path(find_node()).parent if find_node() else None
    if node_dir and str(node_dir) not in env.get("PATH", ""):
        env["PATH"] = str(node_dir) + os.pathsep + env.get("PATH", "")
    # 避免 npm 输出编码在中文 Windows 上报错
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def node_version() -> Optional[str]:
    node = find_node()
    if not node:
        return None
    try:
        r = subprocess.run([node, "--version"], capture_output=True, text=True,
                           timeout=15, env=node_env())
        return r.stdout.strip() or None
    except Exception:
        return None


def npm_version() -> Optional[str]:
    npm = find_npm()
    if not npm:
        return None
    try:
        r = subprocess.run([npm, "--version"], capture_output=True, text=True,
                           timeout=30, env=node_env())
        return r.stdout.strip() or None
    except Exception:
        return None


def npx_argv(extra: List[str]) -> Optional[List[str]]:
    """组装可直接交给 subprocess 的 npx 命令行；未安装 npx 时返回 None"""
    npx = find_npx()
    if not npx:
        return None
    return [npx] + list(extra)


def probe() -> dict:
    """一次性检查运行环境，供 worker 自检与 README 使用"""
    return {
        "platform": sys.platform,
        "node": find_node(),
        "node_version": node_version(),
        "npm": find_npm(),
        "npm_version": npm_version(),
        "npx": find_npx(),
        "ready": bool(find_node() and find_npx()),
    }


if __name__ == "__main__":
    import json
    info = probe()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    raise SystemExit(0 if info["ready"] else 1)
