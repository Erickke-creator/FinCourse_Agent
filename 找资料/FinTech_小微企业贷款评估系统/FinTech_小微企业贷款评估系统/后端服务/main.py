"""
FastAPI backend for SME Loan Evaluation + Bank Matching.
Knowledge-base-aware: loads KB at startup, passes to evaluation engine.

Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import time
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    LoanInput, EvaluationResult, ApiResponse, BankProductResponse,
    KBSourceEntry, KBSourceListResponse, KBMetadataResponse,
)
from bank_engine import evaluate_loan, BANKS_DB

# ---- Knowledge Base loader ----
_KB_LOADER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "kb", "loader")
)
if os.path.isdir(_KB_LOADER_PATH) and _KB_LOADER_PATH not in sys.path:
    sys.path.insert(0, _KB_LOADER_PATH)

try:
    from loader import KnowledgeBase
    from querier import KBQuery
    _KB_AVAILABLE = True
except ImportError:
    KnowledgeBase = None
    KBQuery = None
    _KB_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="小微贷款智能评估助手 API",
    description="SME Loan Self-Assessment + Bank Matching Engine (KB-aware)",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Knowledge Base initialization ----
_kb = None
if _KB_AVAILABLE:
    try:
        _kb = KnowledgeBase()
        health = _kb.health_check()
        logger.info(
            "Knowledge Base loaded: version=%s, files_ok=%d/%d, banks=%d",
            _kb.version.strip().split("\n")[0],
            health.get("files_ok", 0),
            health.get("files_checked", 0),
            health.get("data_stats", {}).get("banks", 0),
        )
        if health.get("load_errors"):
            for err in health["load_errors"]:
                logger.warning("KB load error: %s", err)
    except Exception as e:
        logger.warning("Knowledge Base init failed: %s. Using legacy data.", e)
        _kb = None
else:
    logger.info("Knowledge Base not available. Using legacy hardcoded data.")


@app.get("/")
async def root():
    return {
        "service": "小微贷款智能评估助手 API",
        "version": "3.0.0",
        "status": "running",
        "kb_available": _kb is not None,
    }


@app.get("/api/health")
async def health_check():
    result = {
        "status": "healthy",
        "banks_count": len(BANKS_DB),
        "kb_available": _kb is not None,
    }
    if _kb:
        result["kb_version"] = _kb.version.strip().split("\n")[0]
        result["kb_bank_count"] = len(_kb.banks)
    return result


@app.get("/api/kb/version")
async def kb_version():
    """Return knowledge base version info."""
    if not _kb:
        return {"kb_available": False, "version": "legacy (hardcoded)"}
    return {
        "kb_available": True,
        "version": _kb.version,
        "kb_root": str(_kb.health_check().get("kb_root", "")),
    }


@app.get("/api/kb/metadata")
async def kb_metadata():
    """Return knowledge base metadata: file stats, counts."""
    if not _kb:
        return {"kb_available": False}
    return {"kb_available": True, **_kb.health_check()}


@app.get("/api/banks")
async def list_banks():
    """Return all bank products — sourced from KB if available, else legacy."""
    if _kb:
        banks_raw = _kb.banks
    else:
        banks_raw = BANKS_DB
    banks = [
        BankProductResponse(
            id=b.get("id", ""),
            name=b.get("name", ""),
            type=b.get("type", ""),
            product_name=b.get("product_name", ""),
            loan_type=b.get("loan_type", ""),
            max_amount_credit=b.get("max_amount_credit", 0),
            max_amount_mortgage=b.get("max_amount_mortgage", 0),
            min_rate=b.get("min_rate", b.get("min_interest_rate", 0)),
            max_rate=b.get("max_rate", b.get("max_interest_rate", 0)),
            max_term_years=b.get("max_term_years", 1),
            min_business_years=b.get("min_business_years", 1),
            target_enterprise=b.get("target_enterprise", ""),
        )
        for b in banks_raw
    ]
    return JSONResponse(content={
        "success": True,
        "data": [b.model_dump() for b in banks],
        "count": len(banks),
        "kb_sourced": _kb is not None,
    })


@app.post("/api/evaluate", response_model=ApiResponse)
async def evaluate_loan_application(inp: LoanInput):
    """
    Main evaluation endpoint — KB-aware with traceability.

    Accepts enterprise profile, returns full evaluation + bank matching + KB sources.
    """
    try:
        start_time = time.time()

        # Create KB query session when KB is available
        kb_query = None
        if _kb and KBQuery:
            kb_query = KBQuery(_kb)
            kb_query.reset_sources()

        # Run evaluation
        result: EvaluationResult = evaluate_loan(inp, kb_query=kb_query)
        elapsed = time.time() - start_time

        # Build response dict
        result_dict = result.model_dump()

        # Inject KB traceability into the result dict
        if kb_query is not None:
            result_dict["kb_sources"] = kb_query.get_accessed_sources_dict()
            result_dict["kb_version"] = kb_query.get_kb_version()
        else:
            result_dict["kb_sources"] = []
            result_dict["kb_version"] = "legacy (hardcoded)"

        # Inject metadata
        result_dict["_meta"] = {
            "evaluation_time_ms": round(elapsed * 1000),
            "banks_evaluated": len(result.bank_matches),
            "engine_version": "3.0.0",
            "kb_sourced": kb_query is not None,
            "kb_version": result_dict.get("kb_version", ""),
            "kb_sources_count": len(result_dict.get("kb_sources", [])),
        }

        # Return the result dict directly as data (includes kb_sources and _meta)
        return JSONResponse(content={
            "success": True,
            "data": result_dict,
            "kb_version": result_dict.get("kb_version", ""),
        })
    except Exception as e:
        logger.exception("Evaluation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate/quick")
async def evaluate_quick(inp: LoanInput):
    """Quick evaluation — score + top 5 banks + KB sources count."""
    try:
        kb_query = None
        if _kb and KBQuery:
            kb_query = KBQuery(_kb)
            kb_query.reset_sources()

        result = evaluate_loan(inp, kb_query=kb_query)

        response_data = {
            "score": result.score,
            "risk_level": result.risk_level.value,
            "enterprise_health_score": result.enterprise_health_score,
            "top_bank": result.bank_matches[0].model_dump() if result.bank_matches else None,
            "bank_matches": [b.model_dump() for b in result.bank_matches[:5]],
        }

        if kb_query is not None:
            response_data["kb_sources"] = kb_query.get_accessed_sources_dict()
            response_data["kb_version"] = kb_query.get_kb_version()

        return JSONResponse(content={"success": True, "data": response_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
