"""
FastAPI backend for SME Loan Evaluation + Bank Matching.
Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import (
    LoanInput, EvaluationResult, ApiResponse, BankProductResponse
)
from bank_engine import evaluate_loan, BANKS_DB
from chat_agent import generate_response, get_or_create_session
from enterprise_search import analyze_enterprise
from pydantic import BaseModel as PydanticBase, Field
import time
import uuid

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
    return {"status": "healthy", "banks_count": len(BANKS_DB)}


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

        # Inject timing metadata
        result_dict = result.model_dump()
        result_dict["_meta"] = {
            "evaluation_time_ms": round(elapsed * 1000),
            "banks_evaluated": len(result.bank_matches),
            "engine_version": "2.0.0",
        }

        return ApiResponse(success=True, data=result)
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
    topic: str = ""
    session_id: str = ""

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """AI对话接口：支持风险评估咨询、贷款要求、银行选择等"""
    try:
        if not req.session_id or req.session_id == "default":
            req.session_id = str(uuid.uuid4())[:8]

        reply = generate_response(req.query, req.session_id)
        session = get_or_create_session(req.session_id)

        return ChatResponse(
            success=True,
            reply=reply,
            topic=session.last_topic,
            session_id=req.session_id,
        )
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
