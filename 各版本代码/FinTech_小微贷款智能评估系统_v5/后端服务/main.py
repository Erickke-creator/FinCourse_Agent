"""
FastAPI backend for SME Loan Evaluation + Bank Matching.
Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from models import (
    LoanInput, EvaluationResult, ApiResponse, BankProductResponse
)
from bank_engine import evaluate_loan, BANKS_DB
from chat_agent import run_agent, get_or_create_session, is_llm_available, ALL_TOOLS, TOOL_MAP
from dotenv import load_dotenv
load_dotenv()
from enterprise_search import analyze_enterprise
from pydantic import BaseModel as PydanticBase, Field
from typing import Optional
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
    download_url: Optional[str] = None
    download_label: Optional[str] = None
    autofill_data: Optional[dict] = None      # v5: 自动填表数据

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """v5 AI对话接口：LLM Agent + 知识库工具调用"""
    try:
        if not req.session_id or req.session_id == "default":
            req.session_id = str(uuid.uuid4())[:8]

        reply = await run_agent(req.query, req.session_id)
        session = get_or_create_session(req.session_id)
        download_url = None
        download_label = None
        autofill_data = None
        if session.autofill_data:
            autofill_data = dict(session.autofill_data)
            session.autofill_data = {}
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
            autofill_data=autofill_data,
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
    """流式 AI 对话（SSE）"""
    if not req.session_id or req.session_id == "default":
        req.session_id = str(uuid.uuid4())[:8]

    async def event_stream():
        import httpx
        DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        if not DEEPSEEK_KEY:
            yield f"data: {json_module.dumps({'error': 'AI service not configured'})}\n\n"
            return

        from chat_agent import _build_system_prompt
        session = get_or_create_session(req.session_id)
        messages = [
            {"role": "system", "content": _build_system_prompt()},
            *session.history[-20:],
            {"role": "user", "content": req.query}
        ]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST", "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": messages,
                          "tools": ALL_TOOLS, "temperature": 0.3, "max_tokens": 1500, "stream": True}
                ) as resp:
                    full_reply = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json_module.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                if delta.get("content"):
                                    full_reply += delta["content"]
                                    yield f"data: {json_module.dumps({'text': delta['content']})}\n\n"
                            except Exception:
                                continue
                    # Save to history
                    session.history.append({"role": "user", "content": req.query})
                    session.history.append({"role": "assistant", "content": full_reply})
                    yield f"data: {json_module.dumps({'done': True, 'full': full_reply})}\n\n"
        except Exception as e:
            yield f"data: {json_module.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============================================================
# v5: 银行数据同步（BANKS_DB → bank_products.json）
# ============================================================
@app.post("/api/ml/explain")
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
# ============================================================
# v5: 还款计划表
# ============================================================
@app.get("/api/repayment-schedule")
async def repayment_schedule(amount: float = 100000, rate: float = 6.0, term: int = 12):
    """生成等额本息还款计划表"""
    monthly_rate = rate / 100 / 12
    if monthly_rate > 0:
        monthly_payment = amount * monthly_rate * (1 + monthly_rate) ** term / ((1 + monthly_rate) ** term - 1)
    else:
        monthly_payment = amount / term
    schedule = []
    balance = amount
    total_interest = 0
    for i in range(1, term + 1):
        interest = balance * monthly_rate
        principal = monthly_payment - interest
        balance -= principal
        total_interest += interest
        schedule.append({
            "month": i, "payment": round(monthly_payment, 2),
            "principal": round(principal, 2), "interest": round(interest, 2),
            "balance": round(max(balance, 0), 2),
            "cumulative_interest": round(total_interest, 2),
        })
    return {
        "success": True,
        "amount": amount, "annual_rate": rate, "term_months": term,
        "monthly_payment": round(monthly_payment, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(monthly_payment * term, 2),
        "schedule": schedule,
    }

# ============================================================
# v5: ML 可解释性
# ============================================================
@app.post("/api/ml/explain")
async def explain_ml(inp: LoanInput):
    """返回 ML 预测的特征归因分析"""
    try:
        import numpy as np
        from ml_inference import MLPredictor
        predictor = MLPredictor()
        if not predictor.load_models():
            return {"success": False, "error": "ML 模型不可用"}
        enterprise_dict = {
            "operating_years": inp.operating_years, "monthly_revenue": inp.monthly_revenue,
            "monthly_fixed_cost": inp.monthly_fixed_cost, "existing_liabilities": inp.existing_liabilities,
            "has_overdue_record": 1 if inp.has_overdue_record else 0,
            "has_collateral_or_guarantor": 1 if inp.has_collateral_or_guarantor else 0,
            "has_business_license": 1 if inp.has_business_license else 0,
            "industry": str(inp.industry), "tax_level": str(inp.tax_level),
            "overdue_count_2yr": inp.overdue_count_2yr,
        }
        prob = predictor.predict_default_probability(enterprise_dict)
        # XGBoost feature importance
        importances = predictor.xgb_default.feature_importances_
        feat_names = predictor.feature_cols if hasattr(predictor, 'feature_cols') else [f'feature_{i}' for i in range(24)]
        # Chinese-friendly names
        name_map = {
            'business_age_years': '经营年限', 'annual_revenue_wan': '年营收', 'annual_profit_wan': '年利润',
            'profit_margin': '利润率', 'cash_flow_wan': '现金流', 'asset_liability_ratio': '资产负债率',
            'invalid_invoice_ratio': '无效发票率', 'supplier_count': '供应商数', 'customer_count': '客户数',
            'customer_concentration': '客户集中度', 'tax_score': '纳税评分', 'annual_tax_wan': '年纳税额',
            'has_default_history': '违约历史', 'overdue_count_2yr': '逾期次数', 'credit_inquiry_3m': '征信查询',
            'legal_disputes': '法律纠纷', 'has_real_estate': '不动产', 'real_estate_value_wan': '不动产价值',
            'has_other_collateral': '其他抵押', 'revenue_volatility': '营收波动', 'is_ecommerce': '电商',
            'is_tech_enterprise': '科技企业', 'industry_encoded': '行业', 'tax_level_encoded': '纳税等级',
        }
        top_idx = np.argsort(importances)[-6:][::-1]
        factors = []
        for idx in top_idx:
            name = feat_names[idx] if idx < len(feat_names) else f'feature_{idx}'
            factors.append({"feature": name_map.get(name, name), "importance": round(float(importances[idx]) * 100, 1)})

        verdict = "低风险" if prob and prob < 0.3 else ("中等风险" if prob and prob < 0.6 else "高风险")
        return {"success": True, "default_probability": round(prob, 4) if prob else None, "verdict": verdict, "top_factors": factors[:5]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# v5: Excel 批量评估
# ============================================================
@app.post("/api/evaluate/batch")
async def batch_evaluate(payload: list[LoanInput]):
    """批量评估：接受企业列表 → 返回对比结果"""
    results = []
    for i, inp in enumerate(payload):
        r = evaluate_loan(inp)
        results.append({"index": i, "score": r.score, "risk_level": str(r.risk_level),
                        "enterprise_health_score": r.enterprise_health_score,
                        "top_bank": r.bank_matches[0].bank_name if r.bank_matches else "N/A",
                        "suggested_amount": r.suggested_amount,
                        "monthly_repayment": round(r.monthly_repayment, 0)})
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"success": True, "count": len(results), "ranking": results}

@app.get("/api/admin/sync-banks")
async def sync_banks():
    """将 bank_engine.BANKS_DB 导出为 bank_products.json（统一数据源）"""
    try:
        banks_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "kb", "data", "banks", "bank_products.json"
        )
        banks_list = [{"id": b.get("id",""), "name":b.get("name",""), "type":b.get("type",""),
                       "product_name":b.get("product_name",""), "loan_type":b.get("loan_type",""),
                       "max_amount_credit":b.get("max_amount_credit",0),
                       "min_rate":b.get("min_rate",0), "max_term_years":b.get("max_term_years",0),
                       "min_business_years":b.get("min_business_years",0),
                       "target_enterprise":b.get("target_enterprise","")} for b in BANKS_DB]
        data = {"metadata":{"total_banks":len(banks_list),"source":"bank_engine.BANKS_DB",
                "synced_at":datetime.now().isoformat()},"banks":banks_list}
        os.makedirs(os.path.dirname(banks_json_path), exist_ok=True)
        with open(banks_json_path,"w",encoding="utf-8") as f:
            json_module.dump(data,f,ensure_ascii=False,indent=2)
        return {"success":True,"banks_synced":len(banks_list)}
    except Exception as e:
        return {"success":False,"error":str(e)}

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


# ============================================================
# v5: 静态前端托管（SPA fallback）
# ============================================================
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
os.makedirs(STATIC_DIR, exist_ok=True)

if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
    print(f"[Static] Frontend mounted from {STATIC_DIR}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
