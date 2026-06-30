"""
v5 What-if 敏感性分析 + 反事实解释
"如果有抵押物，分数变多少？" "做什么才能从70分升到85？"
"""
import copy
from typing import Optional
from models import LoanInput, TaxLevel, IndustryType, MerchantType
from bank_engine import evaluate_loan


def what_if(inp: LoanInput, changes: dict) -> dict:
    """
    给定当前 LoanInput + 变更项 → 返回模拟结果对比。
    changes 示例: {"has_collateral_or_guarantor": True, "tax_level": "A"}
    """
    # 原始评估
    original = _summarize(evaluate_loan(inp))

    # 修改后的评估
    modified = copy.deepcopy(inp)
    for key, val in changes.items():
        if hasattr(modified, key):
            val = _coerce(key, val)
            setattr(modified, key, val)
    new = _summarize(evaluate_loan(modified))

    # 计算差异
    score_delta = new["score"] - original["score"]
    dims = {}
    bd_orig = original.get("breakdown", {})
    bd_new = new.get("breakdown", {})
    for k in set(list(bd_orig.keys()) + list(bd_new.keys())):
        dims[k] = round(bd_new.get(k, 0) - bd_orig.get(k, 0), 1)

    return {
        "success": True,
        "original_score": original["score"],
        "new_score": new["score"],
        "score_delta": score_delta,
        "original_risk": original["risk_level"],
        "new_risk": new["risk_level"],
        "dimension_deltas": dims,
        "changes_applied": changes,
        "verdict": (
            f"修改后评分{'提升' if score_delta > 0 else '下降' if score_delta < 0 else '不变'}"
            f"{abs(score_delta):.0f}分，风险等级从{original['risk_level']}变为{new['risk_level']}"
        ),
    }


def counterfactual(inp: LoanInput, target_score: float = 80) -> dict:
    """
    反事实解释：要做什么才能达到目标评分？
    尝试单变量和多变量组合，返回最小改动方案。
    """
    current = _summarize(evaluate_loan(inp))
    if current["score"] >= target_score:
        return {"success": True, "already_achieved": True, "current_score": current["score"],
                "message": f"当前评分{current['score']:.0f}已达标（目标{target_score:.0f}）"}

    # 可尝试的改进项
    upgrades = [
        ("补办营业执照", {"has_business_license": True}),
        ("增加稳定银行流水", {"has_stable_bank_flow": True}),
        ("提供抵押物或担保人", {"has_collateral_or_guarantor": True}),
        ("纳税等级提升至A", {"tax_level": "A"}),
        ("纳税等级提升至B", {"tax_level": "B"}),
    ]

    suggestions = []
    for label, changes in upgrades:
        modified = copy.deepcopy(inp)
        for key, val in changes.items():
            if hasattr(modified, key) and getattr(modified, key) != val:
                setattr(modified, key, _coerce(key, val))
        new = _summarize(evaluate_loan(modified))
        delta = new["score"] - current["score"]
        if delta > 0:
            suggestions.append({
                "action": label, "score_after": new["score"], "score_gain": delta,
                "risk_after": new["risk_level"], "dimensions_improved": {
                    k: round(new["breakdown"].get(k, 0) - current["breakdown"].get(k, 0), 1)
                    for k in current["breakdown"] if new["breakdown"].get(k, 0) > current["breakdown"].get(k, 0)
                },
            })

    # 排序：收益最大优先
    suggestions.sort(key=lambda x: x["score_gain"], reverse=True)

    # 组合最优方案（贪心）
    best_combo = []
    combo_score = current["score"]
    combo_inp = copy.deepcopy(inp)
    for s in suggestions:
        if combo_score >= target_score:
            break
        # Find matching upgrade
        for label, changes in upgrades:
            if label == s["action"]:
                for key, val in changes.items():
                    if hasattr(combo_inp, key):
                        setattr(combo_inp, key, _coerce(key, val))
                break
        combo_score = _summarize(evaluate_loan(combo_inp))["score"]
        best_combo.append(s["action"])

    return {
        "success": True, "current_score": current["score"], "target_score": target_score,
        "gap": round(target_score - current["score"], 0),
        "single_actions": suggestions[:5],
        "recommended_combo": best_combo,
        "combo_score": combo_score,
        "verdict": (
            f"需要{len(best_combo)}项改进可达到{combo_score:.0f}分：{' → '.join(best_combo)}"
            if best_combo and combo_score >= target_score
            else f"即使实施所有可行改进，最高只能达到{combo_score:.0f}分（目标{target_score:.0f}），建议同步改善经营基本面"
        ),
    }


def _coerce(key: str, val):
    """Convert string values to enum types as needed"""
    if key == "tax_level" and isinstance(val, str):
        try: return TaxLevel[val]
        except: return TaxLevel.M
    if key == "industry" and isinstance(val, str):
        try: return IndustryType[val]
        except:
            try: return IndustryType.other
            except: return val
    if key == "merchant_type" and isinstance(val, str):
        try: return MerchantType[val]
        except: return MerchantType.individual
    return val

def _summarize(result) -> dict:
    """提取评估关键字段"""
    return {
        "score": result.score,
        "risk_level": str(result.risk_level).split(".")[-1],
        "breakdown": result.breakdown.model_dump() if hasattr(result.breakdown, 'model_dump') else dict(result.breakdown),
        "enterprise_health_score": result.enterprise_health_score,
        "bank_matches": [{"name": m.bank_name, "prob": m.approval_probability}
                         for m in (result.bank_matches or [])[:3]],
    }
