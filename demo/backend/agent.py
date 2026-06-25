"""
DeFi 健康度监控 Agent — 核心循环
使用 DeepSeek V4 的 Function Call 机制实现 NL → 工具调用 → 分析回复
"""

import json
import os
import httpx
from dotenv import load_dotenv
from tools import TOOLS_SCHEMA, TOOL_MAP

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions"
MAX_TURNS = 5  # 最多 5 轮工具调用，防止死循环
TIMEOUT = 30  # 秒

SYSTEM_PROMPT = """你是一个专业的 DeFi 协议健康度监控助手，致力于帮助用户实时了解 DeFi 协议的风险状况。

## 你的能力
1. 查询任意 DeFi 协议的 TVL（总锁仓价值）和多链分布
2. 获取借贷协议的利用率、借贷总额、清算风险数据
3. 横向对比不同协议的健康指标
4. 评估协议的清算风险等级

## 重要规则
- **始终使用工具函数获取最新数据**，绝不凭空编造或猜测任何数字
- 涉及风险判断时，必须说明判断依据（利用率数值、阈值标准）
- 如果工具返回错误或数据不可用，**如实告知用户**，不要尝试编造
- 分析时给出可操作的建议（如"建议关注 XX 池"、"当前利用率安全"）
- 使用中文回复，金融术语保留英文缩写（如 TVL、USDC、ETH）
- 回复简洁有力，重点信息用 Emoji 或加粗标注

## 风险等级标准
- 🟢 低风险：利用率 < 60%
- 🟢 较低风险：利用率 60%-80%
- 🟡 中等风险：利用率 80%-95%
- 🔴 高风险：利用率 > 95%
"""


def is_available() -> bool:
    """检查 DeepSeek V4 API 是否可用"""
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.startswith("sk-"))


async def run_agent(user_message: str, history: list[dict] | None = None) -> str:
    """
    执行 Agent 循环：
    user_message → DeepSeek V4 → [tool_calls → execute → feedback]×N → final answer
    """
    if not is_available():
        return _fallback_response(user_message)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(history or []),
        {"role": "user", "content": user_message}
    ]

    for turn in range(MAX_TURNS):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    DEEPSEEK_BASE,
                    headers={
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "tools": TOOLS_SCHEMA,
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    }
                )
                resp.raise_for_status()
                result = resp.json()

        except httpx.TimeoutException:
            return "⏱️ DeepSeek 服务响应超时，请稍后重试。"
        except Exception as e:
            return f"❌ AI 服务调用失败: {str(e)}"

        choice = result["choices"][0]
        msg = choice["message"]
        finish_reason = choice.get("finish_reason")

        # LLM 认为不需要调工具，直接返回文本
        if finish_reason == "stop" and msg.get("content"):
            return msg["content"]

        # LLM 要求调工具
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            # 将 LLM 的工具调用消息加入上下文
            messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls
            })

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"])

                # 执行工具（带错误处理）
                tool_func = TOOL_MAP.get(func_name)
                if tool_func:
                    try:
                        tool_result = await tool_func(**func_args)
                    except Exception as e:
                        tool_result = {"success": False, "error": f"工具执行异常: {str(e)}"}
                else:
                    tool_result = {"success": False, "error": f"未知工具: {func_name}"}

                # 工具结果反馈给 LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # 继续循环，让 LLM 处理工具结果
            continue

        # finish_reason 是 stop 但没有 tool_calls，返回内容
        if msg.get("content"):
            return msg["content"]

        # 其他情况（如 length 截断），直接返回
        return "分析过程异常，请简化您的问题重试。"

    # 超过最大轮次
    return "⚠️ 分析过程超时（工具调用轮次过多）。请尝试更具体的问题，如 '查询 Aave 的 TVL'。"


def _fallback_response(user_message: str) -> str:
    """
    无 API Key 时的降级回复（基于关键词匹配 + 建议）
    """
    msg_lower = user_message.lower()

    # 尝试识别用户想查的协议
    known_protocols = ["aave", "compound", "lido", "maker", "uniswap", "curve", "morpho", "eigenlayer"]
    mentioned = [p for p in known_protocols if p in msg_lower]

    if mentioned:
        names = ", ".join(mentioned)
        return (
            f"🔧 **Demo 模式**（未配置 DeepSeek API Key）\n\n"
            f"检测到您想查询 {names} 的数据。当前无法使用 NL 分析。\n\n"
            f"👉 您可以：\n"
            f"1. 访问「仪表盘」Tab 查看 Top 协议实时数据\n"
            f"2. 在项目根目录创建 `.env` 文件，添加 `DEEPSEEK_API_KEY=sk-xxx` 启用完整自然语言分析\n"
            f"3. 直接调用 API 端点：`/api/protocol/{mentioned[0]}`"
        )

    return (
        "🔧 **Demo 模式**（未配置 DeepSeek API Key）\n\n"
        "当前 AI 自然语言分析不可用。\n\n"
        "👉 **启用方法**：在项目根目录创建 `.env` 文件，添加：\n"
        "```\n"
        "DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx\n"
        "```\n"
        "然后重启后端服务。\n\n"
        "💡 **不使用 AI 也能用**：切换到「仪表盘」Tab 查看 Top 协议实时数据。"
    )
