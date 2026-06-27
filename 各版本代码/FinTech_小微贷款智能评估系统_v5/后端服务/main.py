"""
FastAPI backend for SME Loan Evaluation + Bank Matching.
Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import (
    LoanInput, EvaluationResult, ApiResponse, BankProductResponse
)
from bank_engine import evaluate_loan, BANKS_DB
from chat_agent import (
    AgentConfigurationError,
    run_agent,
    get_or_create_session,
    is_llm_available,
)
from dotenv import load_dotenv
load_dotenv()
from enterprise_search import analyze_enterprise
from pydantic import BaseModel as PydanticBase, Field
from typing import Optional
import os
import time
import uuid
from datetime import datetime
from urllib.parse import quote

app = FastAPI(
    title="小微贷款智能评估助手 API",
    description="SME Loan Self-Assessment + Bank Matching Engine",
    version="2.0.0",
)

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"service": "小微贷款智能评估助手 API", "version": "2.0.0", "status": "running"}


@app.get("/api/health")
async def health_check():
    # ML availability
    ml_available = False
    try:
        from ml_inference import MLPredictor
        p = MLPredictor()
        ml_available = p.load_models()
    except Exception:
        pass

    # KB availability
    kb_available = False
    try:
        from kb_bridge import get_kb_summary
        get_kb_summary()
        kb_available = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "5.0.0",
        "banks_count": len(BANKS_DB),
        "ml_available": ml_available,
        "kb_available": kb_available,
        "agent_available": is_llm_available(),
    }


@app.get("/api/banks")
async def list_banks():
    """Return all bank products in the database."""
    banks = [
        BankProductResponse(
            id=b["id"],
            name=b["name"],
            type=b["type"],
            product_name=b["product_name"],
            loan_type=b["loan_type"],
            max_amount_credit=b["max_amount_credit"],
            max_amount_mortgage=b["max_amount_mortgage"],
            min_rate=b["min_rate"],
            max_rate=b["max_rate"],
            max_term_years=b["max_term_years"],
            min_business_years=b["min_business_years"],
            target_enterprise=b["target_enterprise"],
        )
        for b in BANKS_DB
    ]
    return JSONResponse(content={"success": True, "data": [b.model_dump() for b in banks], "count": len(banks)})


@app.post("/api/evaluate", response_model=ApiResponse)
async def evaluate_loan_application(inp: LoanInput):
    """
    Main evaluation endpoint.
    Accepts enterprise profile, returns full evaluation + bank matching results.
    """
    try:
        start_time = time.time()
        result: EvaluationResult = evaluate_loan(inp)
        elapsed = time.time() - start_time

        # Inject metadata
        meta = {
            "evaluation_time_ms": round(elapsed * 1000),
            "banks_evaluated": len(result.bank_matches),
            "engine_version": "5.0.0",
            "ml_available": result.ml_enhanced,
            "ml_enhanced": result.ml_enhanced,
        }

        return ApiResponse(success=True, data=result, meta=meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate/quick")
async def evaluate_quick(inp: LoanInput):
    """Quick evaluation — returns only bank matches + score."""
    try:
        result = evaluate_loan(inp)
        return JSONResponse(content={
            "success": True,
            "data": {
                "score": result.score,
                "risk_level": result.risk_level.value,
                "enterprise_health_score": result.enterprise_health_score,
                "top_bank": result.bank_matches[0].model_dump() if result.bank_matches else None,
                "bank_matches": [b.model_dump() for b in result.bank_matches[:5]],
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Chat Agent Endpoints
# ============================================================

class ChatRequest(PydanticBase):
    query: str
    session_id: str = "default"

class ChatResponse(PydanticBase):
    success: bool = True
    reply: str
    session_id: str = ""
    ai_available: bool = False
    download_url: Optional[str] = None       # v5: PDF 下载链接
    download_label: Optional[str] = None     # v5: 下载按钮文字

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """v5 AI对话接口：LLM Agent + 知识库工具调用"""
    if not is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="Chat Agent 未配置 DEEPSEEK_API_KEY，无 Key 降级回答已禁用。",
        )
    try:
        if not req.session_id or req.session_id == "default":
            req.session_id = str(uuid.uuid4())[:8]

        reply = await run_agent(req.query, req.session_id)
        session = get_or_create_session(req.session_id)
        download_url = None
        download_label = None
        if session.download_url:
            # 构建完整的下载 URL
            download_url = session.download_url
            download_label = f"下载 {session.download_label} 的评估报告"
            # 清除，避免下次对话误带
            session.download_url = ""
            session.download_label = ""

        return ChatResponse(
            success=True,
            reply=reply,
            session_id=req.session_id,
            ai_available=is_llm_available(),
            download_url=download_url,
            download_label=download_label,
        )
    except AgentConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        return ChatResponse(
            success=False,
            reply=f"抱歉，处理您的问题时出错了：{str(e)}",
            session_id=req.session_id,
        )

@app.post("/api/chat/reset")
async def chat_reset(session_id: str = "default"):
    """重置对话会话"""
    from chat_agent import _active_sessions
    if session_id in _active_sessions:
        del _active_sessions[session_id]
    return {"success": True, "message": "会话已重置"}

# ============================================================
# Enterprise Search Endpoint
# ============================================================
class EnterpriseSearchRequest(PydanticBase):
    name: str

@app.post("/api/enterprise/search")
async def search_enterprise(req: EnterpriseSearchRequest):
    """搜索真实企业并返回贷款可行性分析报告"""
    try:
        result = analyze_enterprise(req.name)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "found": False, "message": f"搜索出错：{str(e)}"}

# ============================================================
# v5 报告导出
# ============================================================
class ReportRequest(PydanticBase):
    enterprise_name: str = "企业"
    evaluation_result: Optional[dict] = None  # 可选：传入评估结果，不传则生成默认报告

@app.post("/api/report/pdf")
async def export_report(req: ReportRequest):
    """导出 PDF 贷款评估报告"""
    try:
        from report_pdf import generate_pdf_file
        result_data = req.evaluation_result or {}
        if not result_data:
            from bank_engine import evaluate_loan
            from models import LoanInput
            inp = LoanInput(requested_amount=500000, loan_term=12, industry="other")
            result_data = evaluate_loan(inp).model_dump()
        path = generate_pdf_file(result_data, {"name": req.enterprise_name})
        return {"success": True, "file_path": path, "message": f"PDF 报告已生成"}
    except ImportError:
        return {"success": False, "message": "reportlab 未安装。pip install reportlab"}
    except Exception as e:
        return {"success": False, "message": f"报告生成失败：{str(e)}"}

@app.post("/api/report/pdf-download")
async def download_report(req: ReportRequest):
    """直接下载 PDF 报告（浏览器触发保存）"""
    from fastapi.responses import StreamingResponse
    try:
        from report_pdf import generate_pdf_bytes
        result_data = req.evaluation_result or {}
        if not result_data:
            from bank_engine import evaluate_loan
            from models import LoanInput
            inp = LoanInput(requested_amount=500000, loan_term=12, industry="other")
            result_data = evaluate_loan(inp).model_dump()
        buf = generate_pdf_bytes(result_data, {"name": req.enterprise_name})
        filename = f"贷款评估报告_{req.enterprise_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_url_encode(filename)}"}
        )
    except ImportError:
        return JSONResponse({"success": False, "message": "reportlab 未安装"}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

def _url_encode(s: str) -> str:
    """URL 编码文件名"""
    return quote(s)


# ============================================================
# v5: SSE 流式对话
# ============================================================
from fastapi.responses import StreamingResponse
import json as json_module

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    SSE 兼容对话接口。

    必须复用 run_agent，否则 DeepSeek 返回的 Function Call 只会被当作
    流式文字忽略，导致评估和知识库工具在前端主链上失效。
    """
    if not req.session_id or req.session_id == "default":
        req.session_id = str(uuid.uuid4())[:8]

    async def event_stream():
        if not is_llm_available():
            yield f"data: {json_module.dumps({'error': 'Chat Agent 未配置 DEEPSEEK_API_KEY，无 Key 降级回答已禁用。'}, ensure_ascii=False)}\n\n"
            return
        try:
            reply = await run_agent(req.query, req.session_id)
            yield f"data: {json_module.dumps({'text': reply}, ensure_ascii=False)}\n\n"
            yield f"data: {json_module.dumps({'done': True, 'full': reply}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json_module.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============================================================
# v5: 银行数据同步（BANKS_DB → bank_products.json）
# ============================================================
@app.get("/api/admin/sync-banks")
async def sync_banks():
    """将 bank_engine.BANKS_DB 导出为 bank_products.json（统一数据源）"""
    try:
        banks_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "kb", "data", "banks", "bank_products.json"
        )
        banks_list = []
        for b in BANKS_DB:
            banks_list.append({
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "type": b.get("type", ""),
                "product_name": b.get("product_name", ""),
                "loan_type": b.get("loan_type", ""),
                "max_amount_credit": b.get("max_amount_credit", 0),
                "max_amount_mortgage": b.get("max_amount_mortgage", 0),
                "min_rate": b.get("min_rate", 0),
                "max_rate": b.get("max_rate", 0),
                "max_term_years": b.get("max_term_years", 0),
                "min_business_years": b.get("min_business_years", 0),
                "target_enterprise": b.get("target_enterprise", ""),
                "preferences": b.get("preferences", {}),
                "rejection_sensitivity": b.get("rejection_sensitivity", {}),
            })
        data = {"metadata": {"total_banks": len(banks_list), "source": "bank_engine.BANKS_DB", "synced_at": datetime.now().isoformat()}, "banks": banks_list}
        os.makedirs(os.path.dirname(banks_json_path), exist_ok=True)
        with open(banks_json_path, "w", encoding="utf-8") as f:
            json_module.dump(data, f, ensure_ascii=False, indent=2)
        return {"success": True, "banks_synced": len(banks_list), "target": banks_json_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# v5: 请求日志中间件
# ============================================================
# ============================================================
# v5: 评分历史
# ============================================================
@app.get("/api/scores/history")
async def score_history(session_id: str = "", limit: int = 5):
    """获取最近评分历史（用于对比）"""
    try:
        from chat_history import get_recent_evaluations
        results = get_recent_evaluations(session_id or None, limit)
        return {"success": True, "count": len(results), "history": results}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    # 简洁日志：方法 路径 状态码 耗时
    if request.url.path.startswith("/api/"):
        print(f"[API] {request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
