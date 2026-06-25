"""
DeFi 健康度监控 Agent — FastAPI 后端
"""

import os
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import get_protocol_tvl, get_lending_data, get_top_protocols, assess_risk
from agent import run_agent, is_available


# ============================================================
# FastAPI 应用
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时的日志"""
    print("\n" + "=" * 60)
    print("[OK] DeFi Health Monitor Agent - Demo Backend Started")
    print(f"     API Docs: http://localhost:8000/docs")
    print(f"     H5 Frontend: http://localhost:8000")
    if is_available():
        print("     AI Mode: Enabled (DeepSeek V4)")
    else:
        print("     AI Mode: Disabled (no DEEPSEEK_API_KEY)")
    print("=" * 60 + "\n")
    yield


app = FastAPI(
    title="DeFi 健康度监控 Agent",
    description="基于 DeepSeek V4 + DefiLlama API 的 DeFi 协议健康度分析工具",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Pydantic 模型
# ============================================================
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    timestamp: str
    ai_available: bool


# ============================================================
# API 路由
# ============================================================
@app.get("/api/health")
async def health():
    """后端健康检查"""
    return {
        "status": "ok",
        "ai_available": is_available(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/top")
async def top_protocols(limit: int = 20):
    """获取 TVL Top N 协议列表（仪表盘数据）"""
    return await get_top_protocols(limit)


@app.get("/api/protocol/{name}")
async def protocol_detail(name: str):
    """
    获取单个协议的完整健康数据：
    - TVL 和链分布
    - 借贷数据（如有）
    - 风险评估
    """
    # 并行获取 TVL 和借贷数据
    import asyncio
    tvl_result, lend_result = await asyncio.gather(
        get_protocol_tvl(name),
        get_lending_data(name),
    )

    # 合并结果
    combined = {
        "protocol": name,
        "timestamp": datetime.now().isoformat(),
        "tvl_data": tvl_result,
        "lending_data": lend_result,
    }

    # 如果有借贷数据，附加风险评估
    if lend_result.get("success") and lend_result.get("has_lending_data"):
        utilization = lend_result.get("utilization", 0)
        combined["risk_assessment"] = {
            "utilization": utilization,
            "utilization_pct": f"{utilization * 100:.1f}%",
            "risk_level": assess_risk(utilization),
        }

    return combined


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    NL 对话接口：发送自然语言消息，获取 Agent 分析回复。
    如果未配置 DEEPSEEK_API_KEY，返回降级提示。
    """
    # 限制输入长度
    if len(req.message) > 500:
        return ChatResponse(
            reply="⚠️ 输入过长（超过 500 字符），请精简您的问题。",
            timestamp=datetime.now().isoformat(),
            ai_available=is_available(),
        )

    reply = await run_agent(req.message, req.history)
    return ChatResponse(
        reply=reply,
        timestamp=datetime.now().isoformat(),
        ai_available=is_available(),
    )


# ============================================================
# 前端静态文件
# ============================================================
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@app.get("/")
async def serve_frontend():
    """提供 H5 前端页面"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ============================================================
# 直接启动
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
