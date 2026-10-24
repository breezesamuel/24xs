# -*- coding: utf-8 -*-
"""
mcp_client.py — 最小 MCP (Model Context Protocol) stdio 客户端

背景：`npx -y mcp-lootdrop <tool> <json-args>` 这种把参数当命令行传的做法是错的。
MCP 服务器（如 mcp-lootdrop）启动后打印 "mcp-lootdrop ready (stdio)."，
然后通过 stdin/stdout 说 JSON-RPC 2.0，需要：
    1. initialize            (握手)
    2. notifications/initialized
    3. tools/list            (发现工具)
    4. tools/call            (调用)
本模块实现上述流程，只依赖标准库。
"""
import json
import subprocess
import threading
import queue
from typing import Any, Dict, List, Optional

try:
    from workers.node_bridge import npx_argv, node_env
except ImportError:  # 直接以脚本方式运行时
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from workers.node_bridge import npx_argv, node_env


class MCPError(RuntimeError):
    pass


class MCPStdioClient:
    """一次性启动 MCP 服务器，完成一次调用后关闭。适合脚本/定时任务。"""

    def __init__(self, argv: List[str], timeout: float = 90.0, env: Optional[dict] = None):
        self.argv = list(argv)
        self.timeout = timeout
        self.env = env or node_env()
        self.proc: Optional[subprocess.Popen] = None
        self._stderr: List[str] = []

    # ---------- 生命周期 ----------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def start(self):
        try:
            self.proc = subprocess.Popen(
                self.argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self.env,
            )
        except FileNotFoundError as e:
            raise MCPError(f"无法启动 MCP 服务器 {self.argv[0]}: {e}") from e

        # 后台收集 stderr，避免管道写满导致阻塞
        t = threading.Thread(target=self._drain_stderr, daemon=True)
        t.start()
        return self

    def _drain_stderr(self):
        if not self.proc or not self.proc.stderr:
            return
        for line in self.proc.stderr:
            self._stderr.append(line.rstrip("\n"))

    def close(self):
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    # ---------- JSON-RPC ----------
    def _send(self, obj: Dict[str, Any]):
        if not self.proc or not self.proc.stdin:
            raise MCPError("MCP 进程未启动")
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _read(self) -> Optional[Dict[str, Any]]:
        """读取下一条 JSON-RPC 消息；跳过非 JSON 的启动横幅"""
        if not self.proc or not self.proc.stdout:
            raise MCPError("MCP 进程未启动")
        deadline_lines = 200
        while deadline_lines > 0:
            deadline_lines -= 1
            line = self.proc.stdout.readline()
            if line == "":
                raise MCPError(
                    "MCP 服务器提前关闭。stderr: " + " | ".join(self._stderr[-5:])
                )
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                # 启动横幅/日志行，忽略
                self._stderr.append(line)
                continue
        raise MCPError("MCP 服务器未返回有效 JSON-RPC 响应")

    def request(self, method: str, params: Optional[dict] = None, _id: int = 1) -> Dict[str, Any]:
        msg = {"jsonrpc": "2.0", "id": _id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        resp = self._read()
        if resp is None:
            raise MCPError(f"{method} 无响应")
        if "error" in resp:
            raise MCPError(f"{method} 失败: {resp['error']}")
        return resp.get("result", {})

    def notify(self, method: str, params: Optional[dict] = None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

    # ---------- MCP 语义 ----------
    PROTOCOL_VERSION = "2024-11-05"

    def initialize(self) -> Dict[str, Any]:
        res = self.request("initialize", {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "24xs-capital-automation", "version": "1.0.0"},
        })
        self.notify("notifications/initialized")
        return res

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.request("tools/list", {}, _id=2).get("tools", [])

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        res = self.request("tools/call", {"name": name, "arguments": arguments or {}}, _id=3)
        # MCP 工具结果通常包在 content[] 里
        if isinstance(res, dict) and "content" in res:
            texts = [c.get("text", "") for c in res["content"] if c.get("type") == "text"]
            blob = "\n".join(t for t in texts if t)
            try:
                return json.loads(blob)
            except (json.JSONDecodeError, TypeError):
                return {"content": res["content"], "text": blob,
                        "isError": res.get("isError", False)}
        return res


def call_lootdrop(tool: str, arguments: Optional[dict] = None, timeout: float = 90.0) -> Dict[str, Any]:
    """便捷函数：调用 mcp-lootdrop 的某个工具"""
    argv = npx_argv(["-y", "mcp-lootdrop"])
    if not argv:
        return {"error": "npx 未找到，请安装 Node.js 18+"}
    try:
        with MCPStdioClient(argv, timeout=timeout) as c:
            c.initialize()
            return c.call_tool(tool, arguments or {})
    except MCPError as e:
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    info = {"tools": None, "error": None}
    argv = npx_argv(["-y", "mcp-lootdrop"])
    if not argv:
        print("npx not found")
        raise SystemExit(1)
    try:
        with MCPStdioClient(argv, timeout=120) as c:
            c.initialize()
            tools = c.list_tools()
            info["tools"] = [t.get("name") for t in tools]
            info["schema"] = {
                t.get("name"): (t.get("inputSchema") or {}).get("properties", {})
                for t in tools
            }
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(info, ensure_ascii=False, indent=2))
