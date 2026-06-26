"""
v5 知识库桥接层 — 连接后端与统一知识库 kb/loader
取代 v4 中直接读取 agent_kb/ 目录的旧模式。
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Optional, Any

# ============================================================
# 路径解析 — 从 后端服务/ 向上两级找到 kb/data/
# ============================================================
_BACKEND_DIR = Path(__file__).resolve().parent          # v5/后端服务/
_V5_DIR = _BACKEND_DIR.parent                            # v5/
_VERSIONS_DIR = _V5_DIR.parent                           # 各版本代码/
_KB_DATA = _VERSIONS_DIR / "kb" / "data"                 # 统一知识库数据目录


def _read_csv(filename: str) -> list[dict]:
    """读取 kb/data/ 下的 CSV 文件（UTF-8 BOM）"""
    path = None
    for root, dirs, files in os.walk(str(_KB_DATA)):
        if filename in files:
            path = Path(root) / filename
            break
    if not path:
        return []

    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {}
                for k, v in row.items():
                    if k and k.strip():
                        key = k.strip()
                        val = (v.strip() if v else "")
                        cleaned[key] = val
                rows.append(cleaned)
    except Exception as e:
        print(f"[kb_bridge] Failed to read {filename}: {e}")
    return rows


def _read_json(filename: str) -> Any:
    """读取 kb/data/ 下的 JSON 文件"""
    path = None
    for root, dirs, files in os.walk(str(_KB_DATA)):
        if filename in files:
            path = Path(root) / filename
            break
    if not path:
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[kb_bridge] Failed to read {filename}: {e}")
        return None


# ============================================================
# 知识库查询接口（供 Agent Tool 调用）
# ============================================================

def search_policies(query: str, top_n: int = 5) -> list[dict]:
    """
    在国家级 + 地方级政策中搜索匹配项。
    搜索范围：标题、摘要、关键条件、适用对象。
    """
    national = _read_csv("national_policies.csv")
    provincial = _read_csv("provincial_policies.csv")
    all_policies = []

    for p in national:
        text = f"{p.get('document_title','')} {p.get('summary','')} {p.get('key_condition','')}"
        if any(kw in text for kw in query.split()):
            all_policies.append({**p, "level": "国家级"})

    for p in provincial:
        text = f"{p.get('province','')} {p.get('city','')} {p.get('subsidy_content','')} {p.get('agent_usage','')}"
        if any(kw in text for kw in query.split()):
            all_policies.append({**p, "level": "地方级"})

    return all_policies[:top_n]


def search_banks(industry: str = "", min_amount: float = 0, max_amount: float = 1e12) -> list[dict]:
    """筛选匹配的银行产品"""
    data = _read_json("bank_products.json")
    if not data:
        return []

    banks = data.get("banks", [])
    results = []
    for b in banks:
        # 按金额筛选
        max_credit = float(b.get("max_amount_credit", 0) or 0)
        if max_credit < min_amount:
            continue
        # 按准入行业筛选
        target = b.get("target_enterprise", "")
        if industry and industry not in target:
            continue
        results.append({
            "name": b.get("name", ""),
            "type": b.get("type", ""),
            "product": b.get("product_name", ""),
            "max_amount": max_credit,
            "min_rate": b.get("min_interest_rate"),
            "approval_days": b.get("approval_days"),
            "requirements": b.get("requirements", {}),
            "preferences": b.get("preferences", {}),
        })
    return results


def get_all_banks() -> list[dict]:
    """返回所有 28 家银行产品摘要"""
    data = _read_json("bank_products.json")
    if not data:
        return []
    return [
        {
            "name": b.get("name"),
            "type": b.get("type"),
            "product": b.get("product_name"),
            "max_amount_credit": b.get("max_amount_credit"),
            "min_rate": b.get("min_interest_rate"),
            "max_term": b.get("max_term_years"),
        }
        for b in data.get("banks", [])
    ]


def get_industry_rules(industry_code: str = "") -> dict:
    """查询行业准入规则，可指定行业代码"""
    rows = _read_csv("industry_acceptance.csv")
    if industry_code:
        for r in rows:
            if r.get("行业代码", "") == industry_code:
                return r
        return {}
    return {"industries": rows}


def get_credit_tolerance(bank_type: str = "") -> list[dict]:
    """查询征信容忍度"""
    rows = _read_csv("credit_tolerance.csv")
    if bank_type:
        return [r for r in rows if bank_type in r.get("银行类型", "")]
    return rows


def get_tax_scoring(level: str = "") -> dict:
    """查询纳税等级评分"""
    rows = _read_csv("tax_level_scoring.csv")
    for r in rows:
        if r.get("纳税等级", "") == level:
            return r
    return {}


def get_rejection_factors() -> list[dict]:
    """返回贷款被拒因子权重"""
    return _read_csv("rejection_factors.csv")


def get_subsidy_policies(keywords: str = "") -> list[dict]:
    """搜索贴息/补贴政策"""
    rows = _read_csv("subsidy_policies.csv")
    if keywords:
        return [r for r in rows if any(kw in str(r) for kw in keywords.split())]
    return rows


def get_macro_stats() -> dict:
    """返回宏观统计数据"""
    return _read_json("macro_statistics.json") or {}


def search_cases(industry: str = "", scenario: str = "", top_n: int = 3) -> list[dict]:
    """
    搜索教学案例（优先返回增强版，含诊断链和改进建议）。
    """
    enhanced = _read_csv("teaching_cases_enhanced.csv")
    basic = _read_csv("teaching_cases_basic.csv")

    # 优先增强版
    candidates = enhanced + basic
    results = []
    for c in candidates:
        text = f"{c.get('industry','')} {c.get('scenario','')} {c.get('result','')}"
        score = 0
        if industry and industry in text:
            score += 1
        if scenario and scenario in text:
            score += 1
        if score > 0:
            results.append((score, c))

    results.sort(key=lambda x: -x[0])
    return [
        {
            "id": r.get("case_id", ""),
            "industry": r.get("industry", ""),
            "scenario": r.get("scenario", ""),
            "result": r.get("result", ""),
            "reason": r.get("reason", ""),
            "diagnosis_chain": r.get("diagnosis_chain", ""),
            "improvement_advice": r.get("improvement_advice", ""),
            "recommended_bank": r.get("recommended_bank", ""),
            "recommended_product": r.get("recommended_product", ""),
        }
        for _, r in results[:top_n]
    ]


def get_kb_summary() -> str:
    """返回知识库概览（供 System Prompt 使用）"""
    banks = get_all_banks()
    industries = _read_csv("industry_acceptance.csv")
    policies = _read_csv("national_policies.csv")
    stats = get_macro_stats()

    return f"""知识库概况：
- {len(banks)} 家银行产品（涵盖国有大行、股份制、城商行、互联网银行）
- {len(industries)} 个行业准入等级
- {len(policies)} 条国家级政策 + 24 条地方补贴政策
- 30 基础教学案例 + 20 增强案例（含诊断链）
- 普惠小微贷款余额：{stats.get('普惠小微贷款余额', '32.93万亿')}
"""


# ============================================================
# 工具 Schema（供 DeepSeek V4 Function Call）
# ============================================================
KB_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "搜索国家级和地方级普惠金融政策、贴息补贴规则。输入关键词如'制造业''创业担保''绿色金融'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_banks",
            "description": "根据行业和金额范围筛选匹配的银行贷款产品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "企业行业，如'制造业''批发零售'"},
                    "min_amount": {"type": "number", "description": "最低贷款金额（元）"},
                    "max_amount": {"type": "number", "description": "最高贷款金额（元）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_industry_rules",
            "description": "查询特定行业的准入等级和接受度系数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry_code": {"type": "string", "description": "行业代码（可选，留空返回全部）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_credit_tolerance",
            "description": "查询各类型银行的征信容忍度标准（逾期次数上限、查询次数上限等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank_type": {"type": "string", "description": "银行类型：'国有大行' '股份制' '互联网银行' '外资银行'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_cases",
            "description": "搜索相似行业/场景的教学案例，获取参考诊断和改进建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "行业，如'餐饮''制造业'"},
                    "scenario": {"type": "string", "description": "场景类型：'通过''拒绝''逾期''违约'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_subsidy_policies",
            "description": "搜索2026年贴息补贴政策，如服务业贴息、创业担保贷、绿色金融等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "补贴类型关键词"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_stats",
            "description": "获取最新宏观统计数据：普惠小微贷款余额、增速、银行排名。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]

KB_TOOL_MAP = {
    "search_policies": lambda **kw: search_policies(kw.get("query", "")),
    "search_banks": lambda **kw: search_banks(kw.get("industry", ""), kw.get("min_amount", 0), kw.get("max_amount", 1e12)),
    "get_industry_rules": lambda **kw: get_industry_rules(kw.get("industry_code", "")),
    "get_credit_tolerance": lambda **kw: get_credit_tolerance(kw.get("bank_type", "")),
    "search_cases": lambda **kw: search_cases(kw.get("industry", ""), kw.get("scenario", "")),
    "get_subsidy_policies": lambda **kw: get_subsidy_policies(kw.get("keywords", "")),
    "get_macro_stats": lambda **kw: get_macro_stats(),
}
