# -*- coding: utf-8 -*-
"""
Page-Agent Worker：在浏览器内部署的 AI 工人封装。
核心优势：纯前端 JS，无需 Python/无头浏览器/插件，单实例内存 < 50MB，可大规模并行。
部署模式：
1. 本地：Playwright + page-agent CDN（开发调试）
2. 云端：Cloudflare Workers / Vercel Edge Functions + page-agent（生产并行）
3. 本地离线：Ollama + page-agent（零 API 成本）
"""
import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Callable, Any

WORKERS_DIR = Path(__file__).resolve().parent.parent / "08_军团" / "workers"
WORKERS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class WorkerTask:
    id: str
    name: str
    instruction: str  # 自然语言指令，如 "登录 Twitter，搜索 'AI coding'，点赞前 5 条"
    target_url: str
    model: str = "qwen3.5-plus"  # 或 deepseek-chat, gpt-4o, 本地 ollama 模型
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key_env: str = "DASHSCOPE_API_KEY"
    max_steps: int = 20
    timeout_sec: int = 120
    headless: bool = True
    output_schema: Optional[dict] = None  # 期望的结构化输出 schema

@dataclass
class WorkerResult:
    task_id: str
    success: bool
    output: Any
    steps_taken: int
    duration_sec: float
    error: Optional[str] = None
    screenshots: list[str] = None

class PageAgentWorker:
    """
    通过 Node.js 运行 page-agent 的最小封装。
    生产建议：改用 Playwright 直接加载 page-agent CDN，或部署到 Edge Runtime。
    """

    def __init__(self, worker_dir: Optional[Path] = None):
        self.worker_dir = worker_dir or WORKERS_DIR
        self._ensure_node_env()

    def _ensure_node_env(self):
        """检查 Node/npm/page-agent 可用性。

        必须用 node_bridge 解析绝对路径：Windows 上 npm/npx 只有 .cmd/.ps1
        变体，subprocess 直呼裸 "npm" 会抛 [WinError 2]。
        """
        try:
            from workers.node_bridge import probe
        except ImportError:
            from node_bridge import probe
        info = probe()
        if not info.get("ready"):
            raise RuntimeError(
                "Node.js 未就绪：node=%s npm=%s npx=%s。"
                "请安装 Node.js 18+ 并确保其在 PATH 中。"
                % (info.get("node"), info.get("npm"), info.get("npx"))
            )
        self.node_info = info
        return info

    def _build_worker_script(self, task: WorkerTask) -> str:
        """生成在 Node 中运行的 page-agent 脚本。"""
        api_key = os.getenv(task.api_key_env, "")
        if not api_key:
            raise ValueError(f"环境变量 {task.api_key_env} 未设置")

        return f"""
// page-agent worker script - auto generated
import {{ PageAgent }} from 'page-agent';
import {{ fileURLToPath }} from 'url';
import {{ dirname, join }} from 'path';
import {{ writeFileSync }} from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const agent = new PageAgent({{
    model: '{task.model}',
    baseURL: '{task.base_url}',
    apiKey: '{api_key}',
    language: 'zh-CN',
    maxSteps: {task.max_steps},
}});

async function main() {{
    const results = {{}};
    try {{
        await agent.goto('{task.target_url}');
        const result = await agent.execute('{task.instruction.replace("'", "\\'")}');
        results.success = true;
        results.output = result;
        results.steps = agent.getStepCount?.() || 0;
    }} catch (e) {{
        results.success = false;
        results.error = e.message;
        results.steps = agent.getStepCount?.() || 0;
    }}
    writeFileSync(join(__dirname, 'worker_result_{task.id}.json'), JSON.stringify(results, null, 2));
    process.exit(results.success ? 0 : 1);
}}

main();
"""

    async def execute(self, task: WorkerTask, on_progress: Optional[Callable[[str], None]] = None) -> WorkerResult:
        """执行单个任务。"""
        import time
        start = time.time()

        # 写入临时脚本
        script_path = self.worker_dir / f"worker_{task.id}.mjs"
        script_content = self._build_worker_script(task)
        script_path.write_text(script_content, encoding="utf-8")

        # 确保依赖
        pkg_path = self.worker_dir / "package.json"
        if not pkg_path.exists():
            pkg = {
                "name": "page-agent-workers",
                "type": "module",
                "dependencies": {
                    "page-agent": "^1.12.4"
                }
            }
            pkg_path.write_text(json.dumps(pkg, indent=2), encoding="utf-8")
        try:
            from workers.node_bridge import find_npm, node_env
        except ImportError:
            from node_bridge import find_npm, node_env
        npm = find_npm()
        if not npm:
            raise RuntimeError("npm 未找到，无法安装 page-agent 依赖")
        # Windows 上必须传 npm.cmd 的绝对路径，否则 [WinError 2]
        r = subprocess.run([npm, "install"], cwd=str(self.worker_dir),
                           capture_output=True, text=True, timeout=600, env=node_env())
        if r.returncode != 0:
            raise RuntimeError(f"npm install 失败: {(r.stderr or r.stdout)[-500:]}")

        if on_progress:
            on_progress(f"[Worker {task.id}] Starting: {task.name}")

        node = getattr(self, "node_info", {}).get("node")
        if not node:
            from workers.node_bridge import find_node as _fn
            node = _fn()
        if not node:
            raise RuntimeError("node 未找到")

        try:
            proc = await asyncio.create_subprocess_exec(
                node, str(script_path),
                cwd=str(self.worker_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=task.timeout_sec)

            duration = time.time() - start

            # 读取结果
            result_file = self.worker_dir / f"worker_result_{task.id}.json"
            if result_file.exists():
                result_data = json.loads(result_file.read_text(encoding="utf-8"))
                return WorkerResult(
                    task_id=task.id,
                    success=result_data.get("success", False),
                    output=result_data.get("output"),
                    steps_taken=result_data.get("steps", 0),
                    duration_sec=duration,
                    error=result_data.get("error"),
                    screenshots=[]
                )
            else:
                return WorkerResult(
                    task_id=task.id,
                    success=False,
                    output=None,
                    steps_taken=0,
                    duration_sec=duration,
                    error=f"No result file. stderr: {stderr.decode()[:500] if stderr else 'unknown'}"
                )

        except asyncio.TimeoutError:
            return WorkerResult(
                task_id=task.id,
                success=False,
                output=None,
                steps_taken=0,
                duration_sec=task.timeout_sec,
                error=f"Timeout after {task.timeout_sec}s"
            )
        except Exception as e:
            return WorkerResult(
                task_id=task.id,
                success=False,
                output=None,
                steps_taken=0,
                duration_sec=time.time() - start,
                error=str(e)
            )

    async def execute_batch(self, tasks: list[WorkerTask], concurrency: int = 3) -> list[WorkerResult]:
        """并发执行多个任务。"""
        semaphore = asyncio.Semaphore(concurrency)

        async def run_one(task):
            async with semaphore:
                return await self.execute(task)

        return await asyncio.gather(*[run_one(t) for t in tasks])

# 预置任务模板
class TaskTemplates:
    @staticmethod
    def validate_market_keyword(keyword: str, region: str = "US") -> WorkerTask:
        return WorkerTask(
            id=str(uuid.uuid4())[:8],
            name=f"Market Keyword Validation: {keyword}",
            instruction=f"打开 Google Trends，搜索 '{keyword}' 最近 12 个月趋势，截图保存趋势图，返回趋势方向（上升/下降/平稳）和相关热门查询",
            target_url="https://trends.google.com/trends/",
            max_steps=15,
        )

    @staticmethod
    def scrape_competitor_pricing(competitor_url: str) -> WorkerTask:
        return WorkerTask(
            id=str(uuid.uuid4())[:8],
            name=f"Competitor Pricing: {competitor_url}",
            instruction=f"访问定价页面，提取所有套餐名称、月价格、包含功能、限制条件，返回 JSON 数组",
            target_url=competitor_url,
            max_steps=20,
            output_schema={"type": "array", "items": {"type": "object", "properties": {"plan": {"type": "string"}, "price_monthly_usd": {"type": "number"}, "features": {"type": "array", "items": {"type": "string"}}, "limits": {"type": "array", "items": {"type": "string"}}}}}
        )

    @staticmethod
    def post_to_social(platform: str, content: str, account_hint: str = "") -> WorkerTask:
        urls = {"twitter": "https://x.com/compose/tweet", "linkedin": "https://www.linkedin.com/feed/", "reddit": "https://www.reddit.com/submit"}
        return WorkerTask(
            id=str(uuid.uuid4())[:8],
            name=f"Post to {platform}",
            instruction=f"登录 {platform}（{account_hint}），发布内容：{content}，返回发布后的 URL",
            target_url=urls.get(platform, "https://x.com/compose/tweet"),
            max_steps=15,
        )

    @staticmethod
    def signup_waitlist(landing_url: str, email: str) -> WorkerTask:
        return WorkerTask(
            id=str(uuid.uuid4())[:8],
            name=f"Signup Waitlist: {landing_url}",
            instruction=f"访问落地页，找到邮箱输入框，填入 {email}，提交，返回是否成功及确认信息",
            target_url=landing_url,
            max_steps=10,
        )

    @staticmethod
    def extract_affiliate_links(page_url: str, keyword: str) -> WorkerTask:
        return WorkerTask(
            id=str(uuid.uuid4())[:8],
            name=f"Affiliate Extraction: {keyword}",
            instruction=f"搜索页面中的 '{keyword}' 相关联盟链接/推广码，返回所有找到的链接和佣金比例（如有）",
            target_url=page_url,
            max_steps=15,
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Page-Agent Worker 测试")
    parser.add_argument("--instruction", required=True, help="自然语言指令")
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--model", default="qwen3.5-plus", help="模型名称")
    args = parser.parse_args()

    async def main():
        worker = PageAgentWorker()
        task = WorkerTask(
            id="test001",
            name="CLI Test",
            instruction=args.instruction,
            target_url=args.url,
            model=args.model,
        )
        result = await worker.execute(task)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    asyncio.run(main())