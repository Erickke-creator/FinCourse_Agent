"""
v5 知识库桥接层 — 连接后端与统一知识库 kb/loader
取代 v4 中直接读取 agent_kb/ 目录的旧模式。
"""

import os
import sys
import json
import csv
import re
from pathlib import Path
from typing import Optional, Any

# ============================================================
# 路径解析 — 从 后端服务/ 向上两级找到 kb/data/
# ============================================================
_BACKEND_DIR = Path(__file__).resolve().parent          # v5/后端服务/
_V5_DIR = _BACKEND_DIR.parent                            # v5/
_VERSIONS_DIR = _V5_DIR.parent                           # 各版本代码/
_KB_DATA = _VERSIONS_DIR / "kb" / "data"                 # 统一知识库数据目录


_INDUSTRY_ALIASES = {
    "manufacturing": ("制造业", "制造", "工厂", "生产加工"),
    "wholesale_retail": ("批发零售业", "批发零售", "零售", "批发", "商贸"),
    "it_tech": ("信息技术", "软件服务", "IT", "科技", "互联网"),
    "hospitality_food": ("住宿餐饮", "餐饮", "饭店", "酒店", "餐厅"),
    "transportation": ("交通运输", "物流", "运输"),
    "agriculture": ("农业", "农林牧渔", "三农", "农村"),
    "construction": ("建筑业", "建筑", "工程", "施工"),
    "culture_sports": ("文化体育", "文化", "体育"),
    "scientific_research": ("科学研究", "科研", "研发", "专精特新"),
    "resident_service": ("居民服务", "生活服务", "家政", "美容"),
    "education": ("教育", "培训"),
    "healthcare": ("卫生医疗", "医疗", "健康"),
    "finance": ("金融",),
    "real_estate": ("房地产", "地产"),
    "entertainment": ("娱乐",),
    "mining": ("采矿", "矿业"),
    "energy_utilities": ("能源", "电力", "公用事业"),
}

_REGION_ALIASES = {
    "广东": "广东省", "广东省": "广东省", "深圳": "广东省", "广州": "广东省",
    "浙江": "浙江省", "浙江省": "浙江省", "江苏": "江苏省", "江苏省": "江苏省",
    "山东": "山东省", "山东省": "山东省", "四川": "四川省", "四川省": "四川省",
    "湖北": "湖北省", "湖北省": "湖北省", "福建": "福建省", "福建省": "福建省",
    "河南": "河南省", "河南省": "河南省", "湖南": "湖南省", "湖南省": "湖南省",
    "北京": "北京市", "北京市": "北京市", "上海": "上海市", "上海市": "上海市",
}

_DOMAIN_TERMS = (
    "小微企业", "个体工商户", "普惠金融", "普惠小微", "贷款", "融资",
    "续贷", "贴息", "补贴", "担保", "征信", "创业", "绿色金融", "科技型企业",
    "制造业", "餐饮", "零售", "批发", "农业", "物流", "建筑", "软件", "科技",
)


def normalize_industry(industry: str) -> tuple[str, tuple[str, ...]]:
    """将中英文行业表达归一为后端代码和可检索别名。"""
    raw = str(industry or "").strip()
    lowered = raw.lower()
    for code, aliases in _INDUSTRY_ALIASES.items():
        if lowered == code or any(alias.lower() in lowered for alias in aliases):
            return code, aliases
    return lowered, (raw,) if raw else ()


def _query_terms(query: str) -> list[str]:
    """为中文自然句提取稳定检索词，避免依赖空格分词。"""
    text = str(query or "").strip()
    terms = set()
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_+-]*|[0-9]+(?:\.[0-9]+)?", text):
        if len(token) >= 2:
            terms.add(token.lower())
    for term in (*_DOMAIN_TERMS, *_REGION_ALIASES.keys()):
        if term.lower() in text.lower():
            terms.add(term)
    code, aliases = normalize_industry(text)
    if code in _INDUSTRY_ALIASES:
        terms.update(alias for alias in aliases if alias in text or len(alias) >= 3)
    return sorted(terms, key=len, reverse=True)


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
    if not str(query or "").strip():
        return []

    national = _read_csv("national_policies.csv")
    provincial = _read_csv("provincial_policies.csv")
    terms = _query_terms(query)
    requested_regions = {
        province for alias, province in _REGION_ALIASES.items() if alias in query
    }
    ranked: list[tuple[float, dict]] = []
    seen = set()

    def add_policy(policy: dict, level: str):
        rule_id = policy.get("rule_id", "")
        if rule_id in seen:
            return
        province = policy.get("province", "")
        if level == "地方级" and requested_regions and province not in requested_regions:
            return
        text = " ".join(str(v or "") for v in policy.values())
        score = sum(1 + min(len(term), 6) / 6 for term in terms if term.lower() in text.lower())
        if requested_regions and province in requested_regions:
            score += 4
        if score > 0:
            seen.add(rule_id)
            ranked.append((score, {**policy, "level": level}))

    for policy in provincial:
        add_policy(policy, "地方级")
    for policy in national:
        add_policy(policy, "国家级")

    ranked.sort(key=lambda item: (-item[0], item[1].get("publish_date", "")), reverse=False)
    return [policy for _, policy in ranked[:max(1, int(top_n))]]


def search_banks(
    industry: str = "",
    requested_amount_wan: float = 0,
    tax_level: str = "",
    top_n: int = 5,
) -> list[dict]:
    """
    按申请金额筛选并按行业偏好排序银行产品。

    知识库额度单位为“万元”；行业是软匹配条件，不再因为文案未显式
    写出某行业而将所有产品过滤为空。
    """
    data = _read_json("bank_products.json")
    if not data:
        return []

    banks = data.get("banks", [])
    _, industry_aliases = normalize_industry(industry)
    normalized_tax_level = str(tax_level or "").upper()
    results: list[tuple[int, int, float, float, dict]] = []
    for b in banks:
        max_credit = float(b.get("max_amount_credit", 0) or 0)
        max_mortgage = float(b.get("max_amount_mortgage", 0) or 0)
        max_limit = max(max_credit, max_mortgage)
        if float(requested_amount_wan or 0) > max_limit:
            continue
        target = str(b.get("target_enterprise", ""))
        product_text = f"{target} {b.get('product_name', '')} {b.get('loan_type', '')}"
        industry_match = any(alias and alias in product_text for alias in industry_aliases)
        accepted_tax_levels = b.get("requirements", {}).get("tax_level_required", []) or []
        tax_level_match = not normalized_tax_level or not accepted_tax_levels or normalized_tax_level in accepted_tax_levels
        approval_rate = float(b.get("estimated_approval_rate", 0) or 0)
        min_rate = float(b.get("min_interest_rate", 99) or 99)
        item = {
            "bank_id": b.get("id", ""),
            "name": b.get("name", ""),
            "type": b.get("type", ""),
            "product": b.get("product_name", ""),
            "loan_type": b.get("loan_type", ""),
            "max_amount_credit_wan": max_credit,
            "max_amount_mortgage_wan": max_mortgage,
            "min_rate": b.get("min_interest_rate"),
            "max_rate": b.get("max_interest_rate"),
            "max_term_years": b.get("max_term_years"),
            "approval_days": b.get("approval_days"),
            "requirements": b.get("requirements", {}),
            "preferences": b.get("preferences", {}),
            "target_enterprise": target,
            "industry_match": industry_match,
            "tax_level_match": tax_level_match,
            "estimated_approval_rate": approval_rate,
        }
        results.append((1 if tax_level_match else 0, 1 if industry_match else 0, approval_rate, -min_rate, item))
    results.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    return [item for *_, item in results[:max(1, int(top_n))]]


def get_all_banks() -> list[dict]:
    """返回知识库中所有银行产品摘要。"""
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
        normalized_code, aliases = normalize_industry(industry_code)
        for r in rows:
            if (
                r.get("行业代码", "") == normalized_code
                or industry_code in r.get("行业名称", "")
                or any(alias in r.get("行业名称", "") for alias in aliases)
            ):
                return r
        return {}
    return {"industries": rows}


def get_credit_tolerance(bank_type: str = "") -> list[dict]:
    """查询征信容忍度"""
    rows = _read_csv("credit_tolerance.csv")
    if bank_type:
        aliases = {
            "国有大行": "国有大行",
            "国有大型商业银行": "国有大行",
            "股份制": "股份制/中小银行",
            "中小银行": "股份制/中小银行",
            "互联网银行": "互联网银行",
            "外资银行": "外资银行",
        }
        normalized = aliases.get(bank_type, bank_type)
        return [r for r in rows if normalized in r.get("银行层级", "")]
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
        terms = _query_terms(keywords)
        return [r for r in rows if any(term in str(r) for term in terms)]
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

    _, industry_aliases = normalize_industry(industry)
    scenario_aliases = {
        "通过": ("通过", "获批", "approved"),
        "拒绝": ("拒绝", "未获批", "rejected"),
        "逾期": ("逾期", "overdue"),
        "违约": ("违约", "default"),
    }
    requested_scenarios = tuple(
        alias
        for key, aliases in scenario_aliases.items()
        if key in scenario or scenario.lower() in tuple(a.lower() for a in aliases)
        for alias in aliases
    ) or ((scenario,) if scenario else ())

    # 优先增强版
    candidates = enhanced + basic
    results = []
    for c in candidates:
        text = f"{c.get('industry','')} {c.get('scenario','')} {c.get('result','')}"
        score = 0
        if industry and any(alias and alias in text for alias in industry_aliases):
            score += 2
        if scenario and any(alias and alias.lower() in text.lower() for alias in requested_scenarios):
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
            "description": "根据企业行业和申请金额匹配银行贷款产品。返回的是知识库中15家公开产品，与30家评估引擎分开统计。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "企业行业，如'制造业''批发零售'"},
                    "requested_amount_wan": {"type": "number", "description": "申请贷款金额（万元）"},
                    "tax_level": {"type": "string", "description": "纳税等级 A/B/M/C/D"},
                    "top_n": {"type": "integer", "description": "返回条数，默认5"}
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
    "search_banks": lambda **kw: search_banks(
        kw.get("industry", ""),
        kw.get("requested_amount_wan", 0),
        kw.get("tax_level", ""),
        kw.get("top_n", 5),
    ),
    "get_industry_rules": lambda **kw: get_industry_rules(kw.get("industry_code", "")),
    "get_credit_tolerance": lambda **kw: get_credit_tolerance(kw.get("bank_type", "")),
    "search_cases": lambda **kw: search_cases(kw.get("industry", ""), kw.get("scenario", "")),
    "get_subsidy_policies": lambda **kw: get_subsidy_policies(kw.get("keywords", "")),
    "get_macro_stats": lambda **kw: get_macro_stats(),
}
